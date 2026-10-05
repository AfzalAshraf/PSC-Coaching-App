import test from "node:test";
import assert from "node:assert/strict";
import {
  adaptiveLearningSummary,
  allocateQuotas,
  defaultProfile,
  dueFlashcards,
  exportableProfile,
  generateAptitudeQuestions,
  importProfileBackup,
  normalizeProfile,
  recordSession,
  scheduleFlashcard,
  selectPracticeQuestions,
  validateQuestionPack,
} from "../js/core.js";

const tracks = {
  test: {
    id: "test",
    weights: { knowledge: 60, science: 20, quantitative: 20 },
    domainToBucket: { history: "knowledge", biology: "science", quantitative: "quantitative" },
    availableDomains: ["history", "biology", "quantitative"],
  },
};

const question = (id, domain, answer = "A") => ({
  id,
  domain,
  topic: `${domain} topic`,
  question: `Question ${id}?`,
  options: { A: "Correct option", B: "Wrong one", C: "Wrong two", D: "Wrong three" },
  answer,
  explanation: "A short explanation.",
  mnemonic: "A memory hook.",
  difficulty: 4,
});

test("new profile is dark-first, private and configured for local progress", () => {
  const profile = defaultProfile();
  assert.equal(profile.settings.theme, "dark");
  assert.equal(profile.settings.includeLearningProfile, false);
  assert.deepEqual(profile.stats.mathDrills, { attempts: 0, correct: 0, streak: 0 });
  assert.deepEqual(profile.flashcards, []);
});

test("profile normalization clamps settings and handles malformed values", () => {
  const profile = normalizeProfile({ settings: { track: "not-a-track", dailyGoalMinutes: 900, theme: "neon" }, stats: { recentAttempts: "not-a-list" } });
  assert.equal(profile.settings.track, "10th");
  assert.equal(profile.settings.dailyGoalMinutes, 240);
  assert.equal(profile.settings.theme, "dark");
  assert.deepEqual(profile.stats.recentAttempts, []);
});

test("largest-remainder blueprint quotas sum exactly to requested count", () => {
  const quotas = allocateQuotas(17, { history: 60, science: 20, maths: 20 });
  assert.equal(Object.values(quotas).reduce((sum, value) => sum + value, 0), 17);
  assert.equal(quotas.history, 10);
});

test("question selection respects exam buckets, avoids repeats and preserves shuffled answer", () => {
  const bank = [question("h1", "history"), question("h2", "history"), question("bio1", "biology"), question("m1", "quantitative")];
  const selected = selectPracticeQuestions(bank, { trackId: "test", tracks, count: 4, profile: defaultProfile(), random: () => 0.41 });
  assert.equal(selected.length, 4);
  assert.equal(new Set(selected.map((item) => item.id)).size, 4);
  for (const item of selected) assert.equal(item.options[item.answer], "Correct option");
});

test("session scoring stores behavior, updates weak subjects and turns errors into due cards", () => {
  const profile = defaultProfile();
  const questions = [question("h1", "history"), question("h2", "history"), question("h3", "history")];
  const update = recordSession(profile, {
    questions,
    answers: { h1: "A", h2: "B" },
    hints: { h2: 1 },
    questionTimes: { h1: 13, h2: 96, h3: 5 },
    trackId: "10th",
    mode: "practice",
    elapsedSeconds: 114,
  }, { penalty: 1 / 3, now: new Date("2026-10-05T08:00:00Z") });

  assert.equal(update.result.correct, 1);
  assert.equal(update.result.wrong, 1);
  assert.equal(update.result.skipped, 1);
  assert.equal(update.result.netMarks, 0.67);
  assert.equal(update.profile.flashcards.length, 2);
  assert.equal(update.profile.stats.recentAttempts.find((item) => item.id === "h2").hints, 1);
  assert.equal(update.profile.stats.recentAttempts.find((item) => item.id === "h2").seconds, 96);
  assert.equal(dueFlashcards(update.profile, new Date("2026-10-05T08:01:00Z")).length, 2);

  const summary = adaptiveLearningSummary(update.profile, { history: "History" });
  assert.equal(summary.weakestSubjects[0].subject, "History");
  assert.equal(summary.recentHintsUsed, 1);
  assert.equal(summary.averageQuestionTimeSeconds, 38);
  assert.equal(summary.recurringDifficultTopics[0].topic, "history topic");
});

test("spaced review ratings move a card forward or bring it back soon", () => {
  const start = new Date("2026-10-05T10:00:00Z");
  const session = recordSession(defaultProfile(), { questions: [question("h1", "history")], answers: { h1: "B" } }, { now: start });
  const cardId = session.profile.flashcards[0].id;
  const again = scheduleFlashcard(session.profile, cardId, "again", start);
  const againDue = new Date(again.flashcards[0].dueAt);
  assert.equal((againDue.getTime() - start.getTime()) / 60000, 10);
  const good = scheduleFlashcard(again, cardId, "good", start);
  assert.equal(good.flashcards[0].interval, 1);
  assert.throws(() => scheduleFlashcard(good, cardId, "maybe", start), /valid recall rating/i);
});

test("fresh aptitude questions have four distinct choices and a valid answer", () => {
  const generated = generateAptitudeQuestions(45, () => 0.37);
  assert.equal(generated.length, 45);
  for (const item of generated) {
    assert.equal(new Set(Object.values(item.options)).size, 4);
    assert.equal(item.options[item.answer] !== undefined, true);
    assert.equal(item.domain, "quantitative");
  }
});

test("question-pack import normalizes answers and requires dated sources for current affairs", () => {
  const imported = validateQuestionPack({ questions: [{
    id: "pack-1", domain: "history", topic: "Kerala", question: "Who?",
    options: { A: "A", B: "B", C: "C", D: "D" }, answer: "B", mnemonic: "Remember B",
  }] });
  assert.equal(imported[0].answer, "B");
  assert.equal(imported[0].mnemonic, "Remember B");
  assert.throws(() => validateQuestionPack({ questions: [{
    id: "news-1", domain: "current_affairs", question: "When?",
    options: ["A", "B", "C", "D"], answer: "A",
  }] }), /dated source_hint/i);
});

test("desktop JSON profiles migrate into the browser format without losing study data", () => {
  const imported = importProfileBackup({
    schema_version: 2,
    settings: { track: "degree", daily_goal_minutes: 60, theme: "dark" },
    stats: { sessions: 2, questions: 20, correct: 12, streak: 3, last_study_date: "2026-10-04", domain_stats: { history: { total: 8, correct: 5 } }, trend: [] },
    sessions: [{ track: "degree", count: 10, correct: 6, score_pct: 60, elapsed_seconds: 900 }],
    flashcards: [{ id: "old-1", question: "Question?", answer: "Answer", next_review: "2026-10-05T00:00:00" }],
    custom_questions: [question("teacher-1", "history")],
  });
  assert.equal(imported.settings.track, "degree");
  assert.equal(imported.settings.dailyGoalMinutes, 60);
  assert.equal(imported.stats.domainStats.history.total, 8);
  assert.equal(imported.flashcards[0].answer, "Answer");
  assert.equal(imported.customQuestions[0].id, "teacher-1");
  assert.equal(imported.sessions[0].scorePct, 60);
});

test("backup export excludes provider model configuration and only returns profile data", () => {
  const profile = defaultProfile();
  profile.settings.aiModel = "private-custom-model";
  profile.settings.aiProvider = "openrouter";
  const exported = exportableProfile(profile);
  assert.equal("aiModel" in exported.settings, false);
  assert.equal("aiProvider" in exported.settings, false);
  assert.equal(exported.stats.aiCalls, 0);
});
