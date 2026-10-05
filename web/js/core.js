export const PROFILE_STORAGE_KEY = "kerala-psc-coach.profile.v1";
export const AI_KEY_STORAGE_KEY = "kerala-psc-coach.ai-key";
export const DOMAINS_FALLBACK = {
  history: "History", geography: "Geography", economics: "Economics",
  civics: "Civics & Public Administration", constitution: "Indian Constitution",
  arts: "Arts, Literature, Culture & Sports", biology: "Biology & Public Health",
  physics_chemistry: "Physics & Chemistry", science_technology: "Science & Technology",
  computer: "Computer Science & IT", current_affairs: "Current Affairs",
  quantitative: "Arithmetic & Mental Ability", english: "General English",
  malayalam: "Malayalam", tamil: "Tamil", kannada: "Kannada",
};

const TRACK_IDS = new Set(["10th", "plus_two", "degree"]);
const THEME_NAMES = new Set(["dark", "light", "system"]);
const TEACHING_LANGUAGES = new Set(["English", "Malayalam", "Tamil", "Kannada"]);
const TEACHING_STYLES = new Set(["step-by-step", "examples-first", "quiz-me", "memory-hooks"]);

export function defaultProfile() {
  return {
    schemaVersion: 1,
    settings: {
      track: "10th",
      dailyGoalMinutes: 45,
      negativeMarking: true,
      theme: "dark",
      teachingLanguage: "English",
      teachingStyle: "step-by-step",
      aiProvider: "gemini",
      aiModel: "gemini-3.8-flash",
      includeLearningProfile: false,
    },
    stats: {
      sessions: 0,
      questions: 0,
      correct: 0,
      streak: 0,
      lastStudyDate: "",
      domainStats: {},
      questionStats: {},
      recentAttempts: [],
      trend: [],
      mathDrills: { attempts: 0, correct: 0, streak: 0 },
      aiCalls: 0,
    },
    sessions: [],
    flashcards: [],
    customQuestions: [],
    bookmarks: [],
    dailyChecks: {},
  };
}

function nonnegativeInt(value, fallback = 0) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? Math.max(0, parsed) : fallback;
}

function safeObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function safeList(value, maximum = 1000) {
  return Array.isArray(value) ? value.slice(-maximum) : [];
}

export function normalizeProfile(raw) {
  const profile = defaultProfile();
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return profile;

  const settings = safeObject(raw.settings);
  const track = String(settings.track || "10th");
  const goal = Number.parseInt(settings.dailyGoalMinutes, 10);
  const language = String(settings.teachingLanguage || "English");
  const style = String(settings.teachingStyle || "step-by-step");
  const theme = String(settings.theme || "dark");
  profile.settings = {
    ...profile.settings,
    track: TRACK_IDS.has(track) ? track : "10th",
    dailyGoalMinutes: Number.isFinite(goal) ? Math.max(10, Math.min(240, goal)) : 45,
    negativeMarking: settings.negativeMarking !== false,
    theme: THEME_NAMES.has(theme) ? theme : "dark",
    teachingLanguage: TEACHING_LANGUAGES.has(language) ? language : "English",
    teachingStyle: TEACHING_STYLES.has(style) ? style : "step-by-step",
    aiProvider: ["gemini", "openrouter"].includes(settings.aiProvider) ? settings.aiProvider : "gemini",
    aiModel: String(settings.aiModel || "gemini-3.8-flash").slice(0, 120),
    includeLearningProfile: Boolean(settings.includeLearningProfile),
  };

  const rawStats = safeObject(raw.stats);
  const math = safeObject(rawStats.mathDrills);
  profile.stats = {
    ...profile.stats,
    sessions: nonnegativeInt(rawStats.sessions),
    questions: nonnegativeInt(rawStats.questions),
    correct: nonnegativeInt(rawStats.correct),
    streak: nonnegativeInt(rawStats.streak),
    lastStudyDate: String(rawStats.lastStudyDate || "").slice(0, 10),
    domainStats: safeObject(rawStats.domainStats),
    questionStats: safeObject(rawStats.questionStats),
    recentAttempts: safeList(rawStats.recentAttempts, 300),
    trend: safeList(rawStats.trend, 100),
    mathDrills: {
      attempts: nonnegativeInt(math.attempts),
      correct: nonnegativeInt(math.correct),
      streak: nonnegativeInt(math.streak),
    },
    aiCalls: nonnegativeInt(rawStats.aiCalls),
  };
  profile.sessions = safeList(raw.sessions, 200);
  profile.flashcards = safeList(raw.flashcards, 5000).filter((card) => card && typeof card === "object");
  profile.customQuestions = safeList(raw.customQuestions, 5000).filter((question) => question && typeof question === "object");
  profile.bookmarks = [...new Set(safeList(raw.bookmarks, 5000).map(String))];
  profile.dailyChecks = safeObject(raw.dailyChecks);
  return profile;
}

export function loadProfile(storage) {
  try {
    const target = storage || globalThis.localStorage;
    return normalizeProfile(JSON.parse(target.getItem(PROFILE_STORAGE_KEY) || "null"));
  } catch {
    return defaultProfile();
  }
}

export function saveProfile(profile, storage) {
  const target = storage || globalThis.localStorage;
  const normalized = normalizeProfile(profile);
  target.setItem(PROFILE_STORAGE_KEY, JSON.stringify(normalized));
  return normalized;
}

export function localDateKey(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function allocateQuotas(count, weights) {
  const entries = Object.entries(weights || {}).filter(([, weight]) => Number(weight) > 0);
  const total = entries.reduce((sum, [, weight]) => sum + Number(weight), 0);
  if (!Number.isInteger(count) || count < 0 || !total) throw new RangeError("A valid count and positive weights are required.");
  const quotas = {};
  const fractions = [];
  let allocated = 0;
  for (const [key, weight] of entries) {
    const exact = count * Number(weight) / total;
    const whole = Math.floor(exact);
    quotas[key] = whole;
    allocated += whole;
    fractions.push([key, exact - whole]);
  }
  fractions.sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
  for (let index = 0; index < count - allocated; index += 1) quotas[fractions[index][0]] += 1;
  return quotas;
}

function shuffleInPlace(values, random = Math.random) {
  for (let index = values.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(random() * (index + 1));
    [values[index], values[swap]] = [values[swap], values[index]];
  }
  return values;
}

function formatGeneratedNumber(value) {
  return Number(value.toFixed(2)).toString();
}

function numericOptions(answer, random) {
  const correct = Number(answer);
  const step = Math.max(1, Math.round(Math.abs(correct) / 9) || 1);
  const pool = [
    correct + step, correct - step, correct + step * 2, correct - step * 2,
    correct + step * 3, correct * 2, correct / 2,
  ].filter((value) => Number.isFinite(value) && value >= 0 && Math.abs(value - correct) > 1e-9);
  shuffleInPlace(pool, random);
  const distractors = [];
  for (const value of pool) {
    const text = formatGeneratedNumber(value);
    if (text !== formatGeneratedNumber(correct) && !distractors.includes(text)) distractors.push(text);
    if (distractors.length === 3) break;
  }
  let bump = 1;
  while (distractors.length < 3) {
    const value = formatGeneratedNumber(correct + step * (bump + 3));
    if (value !== formatGeneratedNumber(correct) && !distractors.includes(value)) distractors.push(value);
    bump += 1;
  }
  return distractors;
}

function generatedQuestion(index, prompt, answer, distractors, explanation, topic, mnemonic, difficulty, random) {
  const correct = String(answer);
  const options = [correct, ...distractors.map(String).filter((value) => value !== correct)];
  while (options.length < 4) options.push(formatGeneratedNumber(Number(correct) + options.length + 1));
  const choices = shuffleInPlace(options.slice(0, 4), random);
  const letters = ["A", "B", "C", "D"];
  return {
    id: `generated-${Date.now().toString(36)}-${index}-${Math.floor(random() * 1e9).toString(36)}`,
    domain: "quantitative",
    topic,
    question: prompt,
    options: Object.fromEntries(letters.map((letter, optionIndex) => [letter, choices[optionIndex]])),
    answer: letters[choices.indexOf(correct)],
    explanation,
    mnemonic,
    difficulty,
    source_hint: "Generated practice problem; check the worked explanation.",
  };
}

export function generateAptitudeQuestions(count = 24, random = Math.random) {
  const builders = [
    () => {
      const rate = [5, 10, 12, 15, 20, 25, 30][Math.floor(random() * 7)];
      const number = (Math.floor(random() * 18) + 4) * 100;
      const answer = rate * number / 100;
      return ["Percentages", `${rate}% of ${number} is?`, answer, `Find 10% first, then scale to ${rate}%.`, "10% = divide by 10; 5% is half of 10%.", 2];
    },
    () => {
      const first = Math.floor(random() * 5) + 2;
      const second = Math.floor(random() * 5) + 2;
      const amount = (Math.floor(random() * 8) + 3) * (first + second);
      const answer = amount * first / (first + second);
      return ["Ratio and Proportion", `A sum of ₹${amount} is shared in the ratio ${first}:${second}. What is the first share?`, answer, `Total parts = ${first} + ${second}. One part = ₹${amount} ÷ ${first + second}. The first share is ${first} parts.`, "Add ratio parts, find one part, then multiply by the part asked for.", 3];
    },
    () => {
      const numbers = Array.from({ length: 3 }, () => Math.floor(random() * 30) + 10);
      const total = numbers.reduce((sum, value) => sum + value, 0);
      const answer = total / numbers.length;
      return ["Average", `Find the average of ${numbers.join(", ")}.`, answer, `Add the values: ${numbers.join(" + ")} = ${total}. Divide the total by ${numbers.length}: ${total} ÷ ${numbers.length} = ${formatGeneratedNumber(answer)}.`, "Average × count = total; total ÷ count = average.", 2];
    },
    () => {
      const principal = (Math.floor(random() * 8) + 2) * 1000;
      const rate = [5, 6, 8, 10, 12][Math.floor(random() * 5)];
      const years = Math.floor(random() * 4) + 1;
      const answer = principal * rate * years / 100;
      return ["Simple Interest", `Find the simple interest on ₹${principal} at ${rate}% per year for ${years} years.`, answer, `SI = P × R × T ÷ 100 = ${principal} × ${rate} × ${years} ÷ 100 = ₹${formatGeneratedNumber(answer)}.`, "P-R-T, then divide by 100: Principal × Rate × Time ÷ 100.", 3];
    },
    () => {
      const speed = (Math.floor(random() * 8) + 3) * 5;
      const hours = Math.floor(random() * 5) + 2;
      const answer = speed * hours;
      return ["Time, Speed and Distance", `A vehicle travels at ${speed} km/h for ${hours} hours. How far does it travel?`, answer, `Distance = speed × time = ${speed} × ${hours} = ${answer} km.`, "D-S-T: distance = speed × time; divide to find speed or time.", 2];
    },
    () => {
      const cost = (Math.floor(random() * 10) + 2) * 100;
      const rate = [5, 10, 12, 15, 20, 25][Math.floor(random() * 6)];
      const answer = cost * (100 + rate) / 100;
      return ["Profit and Loss", `An item costs ₹${cost}. At a ${rate}% profit, what is the selling price?`, answer, `Profit = ${rate}% of ₹${cost} = ₹${formatGeneratedNumber(answer - cost)}. Selling price = cost + profit = ₹${formatGeneratedNumber(answer)}.`, "Find the difference first; profit percentage is measured against cost price.", 3];
    },
    () => {
      const a = Math.floor(random() * 8) + 2;
      const b = Math.floor(random() * 8) + 2;
      const answer = 1 / (1 / a + 1 / b);
      return ["Time and Work", `Worker A finishes a job in ${a} days and Worker B in ${b} days. How many days together?`, answer, `A's rate = 1/${a}; B's rate = 1/${b}. Combined rate = 1/${a} + 1/${b} = ${(a + b)}/${a * b}. Time = 1 ÷ combined rate = ${formatGeneratedNumber(answer)} days.`, "Convert each worker to a one-day rate, add the rates, then invert.", 4];
    },
    () => {
      const start = Math.floor(random() * 20) + 2;
      const gap = Math.floor(random() * 8) + 2;
      const terms = [start, start + gap, start + gap * 2, start + gap * 3];
      const answer = start + gap * 4;
      return ["Number Series", `What number comes next? ${terms.join(", ")}, __`, answer, `Each term increases by ${gap}. Add ${gap} to ${terms[terms.length - 1]} to get ${answer}.`, "Check the gaps between neighboring numbers before guessing a rule.", 2];
    },
    () => {
      const marked = (Math.floor(random() * 12) + 4) * 100;
      const rate = [5, 10, 15, 20, 25][Math.floor(random() * 5)];
      const answer = marked * (100 - rate) / 100;
      return ["Discount", `A ₹${marked} item has a ${rate}% discount. What is the sale price?`, answer, `Discount = ${rate}% of ₹${marked} = ₹${formatGeneratedNumber(marked - answer)}. Sale price = marked price − discount = ₹${formatGeneratedNumber(answer)}.`, "Subtract the discount from the marked price to get the sale price.", 3];
    },
  ];

  const generated = [];
  const safeCount = Math.max(0, Math.min(100, Number.parseInt(count, 10) || 0));
  for (let index = 0; index < safeCount; index += 1) {
    const builder = builders[index % builders.length];
    const [topic, prompt, answer, explanation, mnemonic, difficulty] = builder();
    generated.push(generatedQuestion(index, prompt, formatGeneratedNumber(answer), numericOptions(answer, random), explanation, topic, mnemonic, difficulty, random));
  }
  return generated;
}

function questionPriority(question, profile, dueIds) {
  const stats = profile.stats || {};
  const domain = stats.domainStats?.[question.domain];
  const total = Number(domain?.total || 0);
  const accuracy = total ? Number(domain.correct || 0) / total : null;
  let weight = 1;
  if (accuracy !== null) weight += (1 - accuracy) * 2.2;
  const recentForQuestion = (stats.recentAttempts || []).filter((attempt) => attempt.id === question.id).slice(-3);
  if (recentForQuestion.some((attempt) => !attempt.correct)) weight += 1.3;
  if (recentForQuestion.some((attempt) => Number(attempt.hints) > 0)) weight += 0.45;
  if (recentForQuestion.some((attempt) => Number(attempt.seconds) >= 90)) weight += 0.3;
  const topicKey = String(question.topic || "").trim().toLocaleLowerCase();
  const recentForTopic = (stats.recentAttempts || []).filter((attempt) =>
    attempt.domain === question.domain && String(attempt.topic || "").trim().toLocaleLowerCase() === topicKey
  ).slice(-5);
  if (recentForTopic.some((attempt) => !attempt.correct)) weight += 0.55;
  if (dueIds.has(question.id) || dueIds.has(`card-${question.id}`)) weight += 1.8;
  if (accuracy !== null && accuracy < 0.55 && Number(question.difficulty || 4) > 6) weight *= 0.8;
  if (accuracy !== null && accuracy > 0.82 && Number(question.difficulty || 4) > 5) weight += 0.25;
  return Math.max(0.1, weight);
}

function weightedSample(source, count, profile, adaptive, random, dueIds) {
  const pool = [...source];
  const chosen = [];
  const take = Math.min(pool.length, Math.max(0, count));
  for (let draw = 0; draw < take; draw += 1) {
    const weights = pool.map((question) => adaptive ? questionPriority(question, profile, dueIds) : 1);
    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
    let marker = random() * totalWeight;
    let picked = pool.length - 1;
    for (let index = 0; index < pool.length; index += 1) {
      marker -= weights[index];
      if (marker <= 0) {
        picked = index;
        break;
      }
    }
    chosen.push(pool.splice(picked, 1)[0]);
  }
  return chosen;
}

function shuffleOptions(question, random) {
  const answerText = question.options[question.answer];
  const choices = shuffleInPlace(Object.values(question.options), random);
  const letters = ["A", "B", "C", "D"];
  return {
    ...question,
    options: Object.fromEntries(letters.map((letter, index) => [letter, choices[index]])),
    answer: letters[choices.indexOf(answerText)],
  };
}

export function selectPracticeQuestions(questions, { trackId, tracks, count, domain = "all", profile = defaultProfile(), adaptive = true, random = Math.random }) {
  const track = tracks?.[trackId];
  if (!track) throw new RangeError("Choose a valid exam track.");
  const allowed = new Set(track.availableDomains || Object.keys(track.domainToBucket || {}));
  let eligible = [...new Map(questions.map((question) => [question.id, question])).values()]
    .filter((question) => allowed.has(question.domain));
  if (domain && domain !== "all") eligible = eligible.filter((question) => question.domain === domain);
  if (!eligible.length) throw new RangeError("No questions are available for this selection. Add a question pack or choose another subject.");

  const requested = Math.max(1, Number.parseInt(count, 10) || 10);
  const amount = Math.min(requested, eligible.length);
  const dueIds = new Set((profile.flashcards || []).filter((card) => new Date(card.dueAt || card.next_review || 0) <= new Date()).map((card) => card.questionId || card.id));
  let selected = [];
  if (domain && domain !== "all") {
    selected = weightedSample(eligible, amount, profile, adaptive, random, dueIds);
  } else {
    const quotas = allocateQuotas(amount, track.weights);
    const used = new Set();
    const bucketNames = Object.keys(quotas);
    for (const bucket of bucketNames) {
      const candidates = eligible.filter((question) => track.domainToBucket?.[question.domain] === bucket && !used.has(question.id));
      const sample = weightedSample(candidates, quotas[bucket], profile, adaptive, random, dueIds);
      selected.push(...sample);
      for (const question of sample) used.add(question.id);
    }
    if (selected.length < amount) {
      const remaining = eligible.filter((question) => !used.has(question.id));
      selected.push(...weightedSample(remaining, amount - selected.length, profile, adaptive, random, dueIds));
    }
  }
  return shuffleInPlace(selected, random).map((question) => shuffleOptions(question, random));
}

function addFlashcard(profile, question, now) {
  const id = `card-${question.id}`;
  const answer = question.options?.[question.answer] || question.answerText || "";
  const existing = profile.flashcards.find((card) => card.id === id);
  const card = {
    id,
    questionId: question.id,
    question: question.question,
    answer,
    correctOption: question.answer,
    options: question.options || {},
    explanation: question.explanation || "",
    mnemonic: question.mnemonic || "",
    domain: question.domain,
    topic: question.topic || "",
    interval: 0,
    repetitions: 0,
    ease: 2.5,
    dueAt: now.toISOString(),
    addedAt: now.toISOString(),
  };
  if (existing) Object.assign(existing, card);
  else profile.flashcards.push(card);
  return card;
}

export function recordSession(profileInput, quiz, { penalty = 0, now = new Date() } = {}) {
  const profile = normalizeProfile(profileInput);
  const questions = quiz.questions || [];
  const answers = quiz.answers || {};
  const result = {
    total: questions.length,
    correct: 0,
    wrong: 0,
    skipped: 0,
    attempted: 0,
    netMarks: 0,
    scorePct: 0,
    accuracyPct: 0,
    byDomain: {},
    reviews: [],
  };
  const questionStats = profile.stats.questionStats;
  const domainStats = profile.stats.domainStats;
  const dueNow = new Date(now);
  const attemptDate = dueNow.toISOString();

  for (const question of questions) {
    const selected = answers[question.id] || "";
    const answered = ["A", "B", "C", "D"].includes(selected);
    const correct = answered && selected === question.answer;
    if (correct) result.correct += 1;
    else if (answered) result.wrong += 1;
    else result.skipped += 1;
    result.attempted += Number(answered);

    const stats = result.byDomain[question.domain] ||= { total: 0, correct: 0, wrong: 0, skipped: 0, accuracyPct: 0 };
    stats.total += 1;
    stats.correct += Number(correct);
    stats.wrong += Number(answered && !correct);
    stats.skipped += Number(!answered);

    const aggregate = domainStats[question.domain] ||= { total: 0, correct: 0, wrong: 0, skipped: 0 };
    aggregate.total = nonnegativeInt(aggregate.total) + 1;
    aggregate.correct = nonnegativeInt(aggregate.correct) + Number(correct);
    aggregate.wrong = nonnegativeInt(aggregate.wrong) + Number(answered && !correct);
    aggregate.skipped = nonnegativeInt(aggregate.skipped) + Number(!answered);

    const previous = questionStats[question.id] || { total: 0, correct: 0, wrong: 0, skipped: 0 };
    questionStats[question.id] = {
      ...previous,
      total: nonnegativeInt(previous.total) + 1,
      correct: nonnegativeInt(previous.correct) + Number(correct),
      wrong: nonnegativeInt(previous.wrong) + Number(answered && !correct),
      skipped: nonnegativeInt(previous.skipped) + Number(!answered),
      lastAt: attemptDate,
    };
    profile.stats.recentAttempts.push({
      id: question.id,
      domain: question.domain,
      topic: question.topic || "",
      correct: Boolean(correct),
      answered: Boolean(answered),
      hints: nonnegativeInt(quiz.hints?.[question.id]),
      seconds: Math.max(0, Math.round(Number(quiz.questionTimes?.[question.id] || 0))),
      at: attemptDate,
    });
    if (!correct) addFlashcard(profile, question, dueNow);
    result.reviews.push({ question, selected, correct: Boolean(correct), answered: Boolean(answered) });
  }

  result.attempted = result.correct + result.wrong;
  result.netMarks = Math.round((result.correct - result.wrong * Math.max(0, Number(penalty) || 0)) * 100) / 100;
  result.scorePct = result.total ? Math.round(result.netMarks / result.total * 1000) / 10 : 0;
  result.accuracyPct = result.attempted ? Math.round(result.correct / result.attempted * 1000) / 10 : 0;
  for (const domain of Object.values(result.byDomain)) {
    domain.accuracyPct = domain.total ? Math.round(domain.correct / domain.total * 1000) / 10 : 0;
  }

  const today = localDateKey(dueNow);
  const last = profile.stats.lastStudyDate;
  if (last !== today) {
    const yesterday = new Date(dueNow.getFullYear(), dueNow.getMonth(), dueNow.getDate() - 1);
    profile.stats.streak = last === localDateKey(yesterday) ? profile.stats.streak + 1 : 1;
  }
  profile.stats.lastStudyDate = today;
  profile.stats.sessions += 1;
  profile.stats.questions += result.total;
  profile.stats.correct += result.correct;
  profile.stats.recentAttempts = profile.stats.recentAttempts.slice(-300);

  const session = {
    date: attemptDate,
    track: quiz.trackId || profile.settings.track,
    mode: quiz.mode || "practice",
    count: result.total,
    correct: result.correct,
    wrong: result.wrong,
    skipped: result.skipped,
    netMarks: result.netMarks,
    scorePct: result.scorePct,
    accuracyPct: result.accuracyPct,
    elapsedSeconds: Math.max(0, Math.round(Number(quiz.elapsedSeconds || 0))),
  };
  profile.sessions.push(session);
  profile.sessions = profile.sessions.slice(-200);
  profile.stats.trend.push({ date: today, scorePct: result.scorePct, track: session.track });
  profile.stats.trend = profile.stats.trend.slice(-100);
  return { profile, result, session };
}

export function dueFlashcards(profile, now = new Date()) {
  const current = new Date(now).getTime();
  return [...(profile.flashcards || [])]
    .filter((card) => !Number.isNaN(new Date(card.dueAt || card.next_review || 0).getTime()) && new Date(card.dueAt || card.next_review || 0).getTime() <= current)
    .sort((left, right) => new Date(left.dueAt || left.next_review || 0) - new Date(right.dueAt || right.next_review || 0));
}

export function scheduleFlashcard(profileInput, cardId, quality, now = new Date()) {
  const profile = normalizeProfile(profileInput);
  const card = profile.flashcards.find((item) => item.id === cardId);
  if (!card) throw new RangeError("That review card could not be found.");
  if (!["again", "hard", "good", "easy"].includes(quality)) throw new RangeError("Choose a valid recall rating.");
  const date = new Date(now);
  let repetitions = nonnegativeInt(card.repetitions);
  let interval = nonnegativeInt(card.interval);
  let ease = Math.max(1.3, Number(card.ease) || 2.5);
  if (quality === "again") {
    repetitions = 0;
    interval = 0;
    ease = Math.max(1.3, ease - 0.2);
    date.setMinutes(date.getMinutes() + 10);
  } else if (quality === "hard") {
    interval = Math.max(1, Math.round(Math.max(1, interval) * 1.2));
    ease = Math.max(1.3, ease - 0.15);
    date.setDate(date.getDate() + interval);
  } else if (quality === "good") {
    interval = repetitions === 0 ? 1 : repetitions === 1 ? 3 : Math.max(1, Math.round(Math.max(1, interval) * ease));
    repetitions += 1;
    date.setDate(date.getDate() + interval);
  } else {
    interval = repetitions === 0 ? 4 : Math.max(2, Math.round(Math.max(1, interval) * ease * 1.3));
    repetitions += 1;
    ease += 0.15;
    date.setDate(date.getDate() + interval);
  }
  Object.assign(card, {
    repetitions,
    interval,
    ease: Math.round(ease * 100) / 100,
    dueAt: date.toISOString(),
    lastReviewAt: new Date(now).toISOString(),
    lastQuality: quality,
  });
  return profile;
}

export function weakDomains(profile, minimumQuestions = 3) {
  return Object.entries(profile.stats?.domainStats || {})
    .map(([id, stats]) => ({
      id,
      total: nonnegativeInt(stats.total),
      correct: nonnegativeInt(stats.correct),
      accuracyPct: stats.total ? Math.round(stats.correct / stats.total * 1000) / 10 : 0,
    }))
    .filter((entry) => entry.total >= minimumQuestions)
    .sort((left, right) => left.accuracyPct - right.accuracyPct || right.total - left.total);
}

export function createDailyPlan(profile, tracks) {
  const goal = Math.max(10, Math.min(240, Number(profile.settings.dailyGoalMinutes) || 45));
  const due = dueFlashcards(profile).length;
  const weakest = weakDomains(profile)[0]?.id || "history";
  const label = DOMAINS_FALLBACK[weakest] || weakest.replaceAll("_", " ");
  const reviewMinutes = goal <= 15 ? Math.floor(goal / 3) : Math.max(5, Math.round(goal * 0.25));
  const focusMinutes = goal <= 15 ? Math.floor(goal / 3) : Math.max(5, Math.round(goal * 0.45));
  const quizMinutes = Math.max(1, goal - reviewMinutes - focusMinutes);
  const track = tracks?.[profile.settings.track]?.shortName || "selected exam";
  return [
    { id: "review", title: due ? `Review ${due} due flashcard${due === 1 ? "" : "s"}` : "Review saved mistakes", detail: "Recall the answer before revealing it.", minutes: reviewMinutes, action: "review" },
    { id: "focus", title: `Strengthen ${label}`, detail: "Practice a small set in your lowest-scoring area.", minutes: focusMinutes, action: "focus", domain: weakest },
    { id: "mixed", title: "Take a short mixed quiz", detail: `Use the ${track} blueprint and review every explanation.`, minutes: quizMinutes, action: "mixed" },
  ];
}

export function setDailyTask(profile, taskId, done, day = localDateKey()) {
  const checks = profile.dailyChecks || (profile.dailyChecks = {});
  checks[day] = { ...(checks[day] || {}), [taskId]: Boolean(done) };
  for (const oldDay of Object.keys(checks).sort().slice(0, -45)) delete checks[oldDay];
  return profile;
}

export function adaptiveLearningSummary(profile, domains = DOMAINS_FALLBACK) {
  const weakest = weakDomains(profile, 2).slice(0, 5).map((entry) => ({
    subject: domains[entry.id] || entry.id,
    accuracy: `${entry.accuracyPct}%`,
    questions: entry.total,
  }));
  const topicCounts = new Map();
  for (const attempt of (profile.stats?.recentAttempts || []).slice(-100)) {
    if (!attempt.correct && attempt.topic) topicCounts.set(attempt.topic, (topicCounts.get(attempt.topic) || 0) + 1);
  }
  const repeatedConfusions = [...topicCounts.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 5)
    .map(([topic, mistakes]) => ({ topic, mistakes }));
  const recent = (profile.stats?.recentAttempts || []).slice(-100);
  const supportedAttempts = recent.filter((attempt) => Number(attempt.seconds) > 0);
  const averageAnswerSeconds = supportedAttempts.length
    ? Math.round(supportedAttempts.reduce((sum, attempt) => sum + Number(attempt.seconds), 0) / supportedAttempts.length)
    : null;
  const hintUsedCount = recent.filter((attempt) => Number(attempt.hints) > 0).length;
  return {
    examTrack: profile.settings.track,
    preferredLanguage: profile.settings.teachingLanguage,
    teachingStyle: profile.settings.teachingStyle,
    dailyGoalMinutes: profile.settings.dailyGoalMinutes,
    activeStreakDays: profile.stats.streak,
    dueReviewCards: dueFlashcards(profile).length,
    weakestSubjects: weakest,
    recurringDifficultTopics: repeatedConfusions,
    recentHintsUsed: hintUsedCount,
    averageQuestionTimeSeconds: averageAnswerSeconds,
    practiceSessions: profile.stats.sessions,
  };
}

export function validateQuestionPack(data, domainLabels = DOMAINS_FALLBACK) {
  const source = Array.isArray(data) ? data : data?.questions;
  if (!Array.isArray(source) || source.length === 0) throw new Error("The file needs a non-empty questions list.");
  if (source.length > 5000) throw new Error("A question pack can contain at most 5,000 questions.");
  const seen = new Set();
  return source.map((raw, index) => {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error(`Question ${index + 1} must be an object.`);
    const id = String(raw.id || `import-${Date.now()}-${index}`).trim();
    const domain = String(raw.domain || "").trim().toLowerCase();
    const prompt = String(raw.question || raw.prompt || "").trim();
    if (!prompt || prompt.length > 2000) throw new Error(`Question ${index + 1} needs text (maximum 2,000 characters).`);
    if (!Object.hasOwn(domainLabels, domain)) throw new Error(`Question ${index + 1} uses unsupported subject “${domain}”.`);
    if (seen.has(id)) throw new Error(`Duplicate question ID: ${id}`);
    seen.add(id);
    const optionsRaw = raw.options || raw.choices;
    const optionsList = Array.isArray(optionsRaw) ? optionsRaw : ["A", "B", "C", "D"].map((letter) => optionsRaw?.[letter]);
    if (optionsList.length !== 4 || optionsList.some((option) => !String(option ?? "").trim())) throw new Error(`Question ${index + 1} needs four non-empty options.`);
    const values = optionsList.map((option) => String(option).trim());
    if (new Set(values.map((value) => value.toLocaleLowerCase())).size !== 4) throw new Error(`Question ${index + 1} needs four distinct options.`);
    const rawAnswer = raw.answer ?? raw.correct_option ?? raw.correct_answer;
    const answerText = String(rawAnswer ?? "").trim();
    let answerIndex = ["A", "B", "C", "D"].indexOf(answerText.toUpperCase());
    if (answerIndex < 0 && /^[0-3]$/.test(answerText)) answerIndex = Number(answerText);
    if (answerIndex < 0) answerIndex = values.indexOf(answerText);
    if (answerIndex < 0) throw new Error(`Question ${index + 1} answer must be A-D, an option index, or exact option text.`);
    const sourceHint = String(raw.source_hint || raw.source || "").trim();
    if (domain === "current_affairs" && !sourceHint) throw new Error(`Current-affairs question ${index + 1} needs a dated source_hint.`);
    return {
      id,
      domain,
      topic: String(raw.topic || "General practice").trim().slice(0, 120),
      question: prompt,
      options: Object.fromEntries(["A", "B", "C", "D"].map((letter, i) => [letter, values[i]])),
      answer: ["A", "B", "C", "D"][answerIndex],
      explanation: String(raw.explanation || raw.feedback || "").trim().slice(0, 4000),
      mnemonic: String(raw.mnemonic || "").trim().slice(0, 800),
      difficulty: Math.max(1, Math.min(10, Number.parseInt(raw.difficulty, 10) || 4)),
      source_hint: sourceHint.slice(0, 300),
    };
  });
}

export function exportableProfile(profile) {
  const copy = normalizeProfile(profile);
  delete copy.settings.aiProvider;
  delete copy.settings.aiModel;
  copy.stats.aiCalls = 0;
  return copy;
}

export function importProfileBackup(raw) {
  const source = raw?.profile && typeof raw.profile === "object" ? raw.profile : raw;
  if (!source || typeof source !== "object" || Array.isArray(source)) throw new Error("The backup file is not a profile object.");
  const settings = safeObject(source.settings);
  const oldStats = safeObject(source.stats);
  const domainStats = oldStats.domainStats || oldStats.domain_stats || {};
  const sessions = safeList(source.sessions, 200).map((session) => ({
    ...session,
    netMarks: session.netMarks ?? session.net_marks ?? session.correct ?? 0,
    scorePct: session.scorePct ?? session.score_pct ?? 0,
    accuracyPct: session.accuracyPct ?? session.accuracy_pct ?? 0,
    elapsedSeconds: session.elapsedSeconds ?? session.elapsed_seconds ?? 0,
  }));
  const flashcards = safeList(source.flashcards, 5000).map((card) => ({
    ...card,
    questionId: card.questionId || card.question_id || card.id,
    dueAt: card.dueAt || card.next_review || card.nextReview || new Date().toISOString(),
    addedAt: card.addedAt || card.added || "",
  }));
  const mapped = {
    schemaVersion: 1,
    settings: {
      track: settings.track || "10th",
      dailyGoalMinutes: settings.dailyGoalMinutes ?? settings.daily_goal_minutes ?? 45,
      negativeMarking: settings.negativeMarking ?? settings.negative_marking ?? true,
      theme: settings.theme || "dark",
      teachingLanguage: settings.teachingLanguage || "English",
      teachingStyle: settings.teachingStyle || "step-by-step",
    },
    stats: {
      sessions: oldStats.sessions || sessions.length,
      questions: oldStats.questions || 0,
      correct: oldStats.correct || 0,
      streak: oldStats.streak || 0,
      lastStudyDate: oldStats.lastStudyDate || oldStats.last_study_date || "",
      domainStats: Object.fromEntries(Object.entries(safeObject(domainStats)).map(([domain, rawEntry]) => {
        const entry = safeObject(rawEntry);
        return [domain, {
          ...entry,
          total: entry.total || 0,
          correct: entry.correct || 0,
          wrong: entry.wrong || 0,
          skipped: entry.skipped || 0,
        }];
      })),
      questionStats: oldStats.questionStats || {},
      recentAttempts: oldStats.recentAttempts || [],
      trend: oldStats.trend || [],
      mathDrills: oldStats.mathDrills || { attempts: 0, correct: 0, streak: 0 },
    },
    sessions,
    flashcards,
    customQuestions: source.customQuestions || source.custom_questions || [],
    bookmarks: source.bookmarks || [],
    dailyChecks: source.dailyChecks || source.daily_checks || {},
  };
  const profile = normalizeProfile(mapped);
  if (profile.stats.questions === 0 && sessions.length) {
    profile.stats.questions = sessions.reduce((sum, session) => sum + (Number(session.count) || 0), 0);
    profile.stats.correct = sessions.reduce((sum, session) => sum + (Number(session.correct) || 0), 0);
  }
  return profile;
}
