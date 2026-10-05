import test from "node:test";
import assert from "node:assert/strict";
import { AI_PROVIDERS, askTutor, buildTutorSystemPrompt } from "../js/ai.js";
import { defaultProfile, recordSession } from "../js/core.js";

const makeResponse = (payload, ok = true, status = 200) => ({ ok, status, json: async () => payload });
const weakProfile = () => {
  const question = (id, domain) => ({ id, domain, topic: "Fractions", question: "One?", options: { A: "right", B: "no", C: "no2", D: "no3" }, answer: "A", difficulty: 4 });
  return recordSession(defaultProfile(), {
    questions: [question("m1", "quantitative"), question("m2", "quantitative"), question("m3", "quantitative")],
    answers: { m1: "B", m2: "B", m3: "A" }, hints: { m1: 1 }, questionTimes: { m1: 110, m2: 15, m3: 20 },
  }).profile;
};

test("tutor prompt adapts language and style without leaking unshared study history", () => {
  const profile = weakProfile();
  profile.settings.teachingLanguage = "Malayalam";
  profile.settings.teachingStyle = "examples-first";
  const hidden = buildTutorSystemPrompt({ profile, includeLearningProfile: false, domains: { quantitative: "Arithmetic" }, trackName: "Degree Level" });
  assert.match(hidden, /Reply in Malayalam/);
  assert.match(hidden, /familiar everyday example/);
  assert.match(hidden, /No saved learning history was shared/);
  assert.doesNotMatch(hidden, /weakestSubjects/);

  const shared = buildTutorSystemPrompt({ profile, includeLearningProfile: true, domains: { quantitative: "Arithmetic" }, trackName: "Degree Level" });
  assert.match(shared, /Arithmetic/);
  assert.match(shared, /recurringDifficultTopics/);
  assert.match(shared, /explicitly chose to share/);
});

test("Gemini calls use its HTTPS endpoint and send the key only in an auth header", async () => {
  let request;
  const response = await askTutor({
    provider: "gemini",
    model: AI_PROVIDERS.gemini.defaultModel,
    apiKey: "gem-test-key",
    prompt: "Explain ratios.",
    systemPrompt: "Teach in short steps.",
    fetchImpl: async (url, options) => {
      request = { url, options };
      return makeResponse({ modelVersion: "gemini-test", candidates: [{ content: { parts: [{ text: "A ratio compares quantities." }] } }], usageMetadata: { totalTokenCount: 18 } });
    },
  });
  assert.equal(request.url, "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent");
  assert.equal(request.options.headers["x-goog-api-key"], "gem-test-key");
  assert.equal(request.url.includes("gem-test-key"), false);
  assert.equal(JSON.stringify(request.options.body).includes("gem-test-key"), false);
  assert.equal(response.text, "A ratio compares quantities.");
  assert.equal(response.model, "gemini-test");
});

test("OpenRouter uses bearer auth, bounded output and current chat-completions endpoint", async () => {
  let request;
  const response = await askTutor({
    provider: "openrouter",
    model: "openrouter/free",
    apiKey: "or-test-key",
    prompt: "Give one memory hook.",
    history: [{ role: "assistant", content: "Earlier lesson" }],
    systemPrompt: "Patient PSC tutor.",
    fetchImpl: async (url, options) => {
      request = { url, options };
      return makeResponse({ model: "provider/model", choices: [{ message: { content: "Try this acronym." } }], usage: { total_tokens: 25 } });
    },
  });
  assert.equal(request.url, "https://openrouter.ai/api/v1/chat/completions");
  assert.equal(request.options.headers.Authorization, "Bearer or-test-key");
  assert.equal(JSON.parse(request.options.body).max_tokens, 1200);
  assert.equal(response.model, "provider/model");
  assert.equal(response.text, "Try this acronym.");
});

test("AI does not call a provider without a personal key and surfaces provider errors", async () => {
  await assert.rejects(() => askTutor({ provider: "gemini", prompt: "Help", apiKey: "" }), /own provider API key/i);
  await assert.rejects(() => askTutor({
    provider: "gemini", model: "gemini-test", apiKey: "key", prompt: "Help",
    fetchImpl: async () => makeResponse({ error: { message: "Quota exceeded" } }, false, 429),
  }), /Quota exceeded/);
});
