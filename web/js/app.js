import { AI_PROVIDERS, askTutor, buildTutorSystemPrompt } from "./ai.js";
import {
  AI_KEY_STORAGE_KEY,
  DOMAINS_FALLBACK,
  createDailyPlan,
  defaultProfile,
  dueFlashcards,
  exportableProfile,
  generateAptitudeQuestions,
  importProfileBackup,
  loadProfile,
  localDateKey,
  normalizeProfile,
  recordSession,
  saveProfile,
  scheduleFlashcard,
  selectPracticeQuestions,
  setDailyTask,
  validateQuestionPack,
  weakDomains,
} from "./core.js";
import { MATH_CALCULATORS, formatMathNumber, generateMathDrill, mathAnswerMatches, solveMath } from "./math.js";

const appRoot = document.querySelector("#app");
const toastRoot = document.querySelector("#toast-root");
const NAV_ITEMS = [
  ["home", "Today", "⌂"],
  ["practice", "Practice", "✎"],
  ["review", "Review", "↻"],
  ["ai", "AI Coach", "✦"],
  ["math", "Math Lab", "∑"],
  ["syllabus", "Syllabus", "▤"],
  ["progress", "Progress", "⌁"],
  ["settings", "Settings", "⚙"],
];
const PRIMARY_MOBILE = new Set(["home", "practice", "review", "ai"]);

let catalog = null;
let profile = loadProfile();
let currentPage = "home";
let quiz = null;
let lastResult = null;
let quizTimer = null;
let deferredInstallPrompt = null;
let currentMathResult = null;
let currentMathKind = "percent_of";
let currentMathTarget = "distance";
let currentMathDrill = null;
let mathDrillResult = null;
let reviewQueue = [];
let reviewRevealed = false;
let aiHistory = [];
let aiBusy = false;
let aiPrefill = "";
let aiKey = "";
let rememberAIKey = false;
let aiUsageLabel = "";

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[character]);
}

function percent(value) {
  const number = Number(value) || 0;
  return `${Number.isInteger(number) ? number : number.toFixed(1)}%`;
}

function dateLabel(value, options = { month: "short", day: "numeric" }) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat(undefined, options).format(date);
}

function displayDuration(seconds) {
  const safe = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = Math.floor(safe / 60);
  const remainder = safe % 60;
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function labelForDomain(domain) {
  return catalog?.domains?.[domain] || DOMAINS_FALLBACK[domain] || String(domain || "").replaceAll("_", " ");
}

function getTrack(trackId = profile.settings.track) {
  return catalog?.tracks?.[trackId] || catalog?.tracks?.["10th"];
}

function themeName() {
  return profile.settings.theme === "system"
    ? (globalThis.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark")
    : profile.settings.theme;
}

function save() {
  try {
    profile = saveProfile(profile);
    return true;
  } catch (error) {
    toast(`Could not save this device's study profile: ${error.message}`, "error");
    return false;
  }
}

function toast(message, kind = "") {
  if (!toastRoot) return;
  const item = document.createElement("div");
  item.className = `toast ${kind}`.trim();
  item.textContent = String(message);
  toastRoot.append(item);
  setTimeout(() => item.remove(), 4200);
}

function selected(value, current) {
  return String(value) === String(current) ? " selected" : "";
}

function optionMarkup(value, label, current) {
  return `<option value="${esc(value)}"${selected(value, current)}>${esc(label)}</option>`;
}

function trackOptions(value = profile.settings.track) {
  return Object.entries(catalog.tracks).map(([id, track]) => optionMarkup(id, track.name, value)).join("");
}

function navButton([id, text, symbol], active, mobile = false) {
  return `<button class="nav-button${active === id ? " active" : ""}" type="button" data-action="navigate" data-page="${id}"${active === id ? ' aria-current="page"' : ""}>
    <span class="nav-symbol" aria-hidden="true">${symbol}</span><span>${text}</span>${mobile ? "" : ""}
  </button>`;
}

function renderTopbar() {
  const label = themeName() === "dark" ? "Switch to light appearance" : "Switch to dark appearance";
  const providerReady = aiKey ? "AI key ready" : "Local progress";
  return `<header class="topbar">
    <button class="brand" type="button" data-action="navigate" data-page="home" aria-label="Kerala PSC Coach home">
      <span class="brand-mark" aria-hidden="true">PSC</span>
      <span class="brand-copy"><span class="brand-name">Kerala PSC Coach</span><span class="brand-caption">Study smarter. Remember longer.</span></span>
    </button>
    <div class="topbar-spacer"></div>
    <label class="track-control"><span>Preparing for</span><select class="select-control" aria-label="Exam track" id="global-track">${trackOptions()}</select></label>
    <span class="network-pill${navigator.onLine ? "" : " offline"}" id="network-pill"><span class="network-dot"></span><span id="network-label">${navigator.onLine ? providerReady : "Offline mode"}</span></span>
    <div class="top-actions">
      <button class="button ghost install-button" type="button" data-action="install-app" title="Install or add this app">Install app</button>
      <button class="icon-button" type="button" data-action="toggle-theme" aria-label="${label}" title="${label}">${themeName() === "dark" ? "☼" : "☾"}</button>
      <button class="icon-button" type="button" data-action="navigate" data-page="settings" aria-label="Settings" title="Settings">⚙</button>
    </div>
  </header>`;
}

function renderSidebar() {
  return `<aside class="sidebar" aria-label="Main navigation">
    <div class="nav-group-label">Your study space</div>
    <nav class="nav-list">${NAV_ITEMS.map((item) => navButton(item, currentPage)).join("")}</nav>
    <div class="sidebar-spacer"></div>
    <div class="sidebar-note"><strong>Offline-first by design</strong>Practice, review and progress work on this device. AI tutoring is optional and only runs when you choose a provider.</div>
  </aside>`;
}

function renderMobileNav() {
  const primary = NAV_ITEMS.filter(([id]) => PRIMARY_MOBILE.has(id));
  return `<nav class="mobile-nav" aria-label="Mobile navigation">
    ${primary.map((item) => navButton(item, currentPage, true)).join("")}
    <button class="nav-button" type="button" data-action="open-more" aria-label="More sections"><span class="nav-symbol" aria-hidden="true">•••</span><span>More</span></button>
  </nav>`;
}

function renderMoreDialog() {
  const moreItems = NAV_ITEMS.filter(([id]) => !PRIMARY_MOBILE.has(id));
  return `<dialog class="mobile-more" id="more-dialog" aria-labelledby="more-title">
    <div class="between"><h2 id="more-title">More study tools</h2><button class="icon-button" type="button" data-action="close-more" aria-label="Close">×</button></div>
    <div class="mobile-more-grid">${moreItems.map((item) => navButton(item, currentPage)).join("")}</div>
  </dialog>`;
}

function renderShell(content) {
  const active = document.activeElement;
  const focusIdentity = active && appRoot.contains(active)
    ? {
      id: active.id,
      tag: active.tagName.toLowerCase(),
      attributes: [...active.attributes].filter((attribute) => attribute.name.startsWith("data-")).map((attribute) => [attribute.name, attribute.value]),
    }
    : null;
  appRoot.innerHTML = `<div class="app-shell">
    ${renderTopbar()}
    <div class="workspace">${renderSidebar()}<main class="main" id="main-content" tabindex="-1" aria-labelledby="page-title">${content}</main></div>
    ${renderMobileNav()}${renderMoreDialog()}
  </div>`;
  if (focusIdentity) {
    const candidates = focusIdentity.id
      ? [document.getElementById(focusIdentity.id)].filter(Boolean)
      : [...appRoot.getElementsByTagName(focusIdentity.tag)].filter((element) => focusIdentity.attributes.length && focusIdentity.attributes.every(([name, value]) => element.getAttribute(name) === value));
    const target = candidates.find((element) => !element.disabled);
    const fallback = appRoot.querySelector('#main-content .feedback-box, #main-content [role="status"], #main-content .flashcard-answer, #main-content');
    (target || fallback)?.focus({ preventScroll: true });
  }
  document.documentElement.dataset.theme = themeName();
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = themeName() === "dark" ? "#0c1411" : "#f3f6f3";
  if (currentPage === "quiz") refreshClockView();
}

function render() {
  if (!catalog) return;
  const content = currentPage === "home" ? renderHome()
    : currentPage === "practice" ? renderPractice()
      : currentPage === "quiz" ? renderQuiz()
        : currentPage === "results" ? renderResults()
          : currentPage === "review" ? renderReview()
            : currentPage === "ai" ? renderAI()
              : currentPage === "math" ? renderMathLab()
                : currentPage === "syllabus" ? renderSyllabus()
                  : currentPage === "progress" ? renderProgress()
                    : renderSettings();
  renderShell(content);
}

function header(eyebrow, title, subtitle) {
  return `<div class="page-heading"><div class="eyebrow">${esc(eyebrow)}</div><h1 id="page-title">${esc(title)}</h1><p>${esc(subtitle)}</p></div>`;
}

function currentCounts() {
  const questions = [...catalog.questions, ...profile.customQuestions];
  const counts = {};
  for (const question of questions) counts[question.domain] = (counts[question.domain] || 0) + 1;
  return counts;
}

function renderSubjectRows(domains, limit = 8) {
  if (!domains.length) return `<p class="small-text muted">Your subject-level results will appear here after a few practice sessions.</p>`;
  return domains.slice(0, limit).map((entry) => {
    const good = entry.accuracyPct >= 70;
    const width = Math.max(0, Math.min(100, entry.accuracyPct));
    return `<div class="subject-row"><div class="subject-name" title="${esc(labelForDomain(entry.id))}">${esc(labelForDomain(entry.id))}</div>
      <div class="progress-track ${good ? "" : "gold"}" role="progressbar" aria-valuenow="${Math.round(width)}" aria-valuemin="0" aria-valuemax="100" aria-label="${esc(labelForDomain(entry.id))} accuracy"><span style="width:${width}%"></span></div>
      <div class="subject-meta">${percent(entry.accuracyPct)} · ${entry.total}</div></div>`;
  }).join("");
}

function weekActivity() {
  const today = new Date();
  const dates = Array.from({ length: 7 }, (_, index) => {
    const day = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (6 - index));
    return { key: localDateKey(day), label: new Intl.DateTimeFormat(undefined, { weekday: "short" }).format(day).slice(0, 2), count: 0 };
  });
  const counts = new Map(dates.map((item) => [item.key, item]));
  for (const session of profile.sessions) {
    const key = String(session.date || "").slice(0, 10);
    if (counts.has(key)) counts.get(key).count += 1;
  }
  const max = Math.max(1, ...dates.map((item) => item.count));
  return `<div class="week-grid">${dates.map((item) => `<div class="week-day"><div class="week-bar-holder"><div class="week-bar${item.count ? " active" : ""}" style="height:${item.count ? Math.max(12, item.count / max * 100) : 5}%" title="${item.count} session${item.count === 1 ? "" : "s"}"></div></div><span>${item.label}</span></div>`).join("")}</div>`;
}

function renderPlan() {
  const tasks = createDailyPlan(profile, catalog.tracks);
  const checks = profile.dailyChecks[localDateKey()] || {};
  const complete = tasks.filter((task) => checks[task.id]).length;
  const minutesDone = tasks.filter((task) => checks[task.id]).reduce((sum, task) => sum + task.minutes, 0);
  const goal = Number(profile.settings.dailyGoalMinutes) || 45;
  const pct = tasks.reduce((sum, task) => sum + task.minutes, 0) ? minutesDone / tasks.reduce((sum, task) => sum + task.minutes, 0) * 100 : 0;
  return `<section class="card">
    <div class="card-heading"><div><h2>Today's study plan</h2><p>${goal} minutes · small recall sessions work better than rereading.</p></div><span class="badge accent">${complete}/${tasks.length} done</span></div>
    <div class="progress-track" style="margin:14px 0 7px"><span style="width:${pct}%"></span></div>
    <div class="small-text muted" style="margin-bottom:9px">${minutesDone} of ${goal} planned minutes checked off</div>
    ${tasks.map((task) => `<div class="plan-task${checks[task.id] ? " is-done" : ""}">
      <input type="checkbox" data-task-toggle="${esc(task.id)}" aria-label="Mark ${esc(task.title)} complete"${checks[task.id] ? " checked" : ""}>
      <div><div class="plan-title">${esc(task.title)}</div><div class="plan-detail">${esc(task.detail)}</div></div>
      <div class="plan-minutes">${task.minutes} min · <button class="button small ghost" type="button" data-action="run-task" data-task="${esc(task.action)}" data-domain="${esc(task.domain || "")}">Start</button></div>
    </div>`).join("")}
  </section>`;
}

function renderHome() {
  const stats = profile.stats;
  const accuracy = stats.questions ? stats.correct / stats.questions * 100 : 0;
  const track = getTrack();
  const due = dueFlashcards(profile).length;
  const weak = weakDomains(profile);
  const activity = weekActivity();
  const recent = profile.sessions.slice(-5).reverse();
  return `<div class="page">
    <section class="hero">
      <div><div class="eyebrow">Your personal PSC study plan</div><h1>Get a little stronger<br>every study session.</h1>
        <p>${esc(track.description)} Your practice history guides the next set of questions; no account or internet is needed for core study tools.</p>
        <div class="hero-actions"><button class="button primary" type="button" data-action="navigate" data-page="practice">Start a practice set <span aria-hidden="true">→</span></button><button class="button" type="button" data-action="navigate" data-page="review">Review ${due} due cards</button><button class="button ghost" type="button" data-action="navigate" data-page="ai">Ask your tutor</button></div>
      </div>
      <div class="hero-side"><span class="hero-streak">${stats.streak || 0}</span><span class="hero-streak-label">day study streak</span></div>
    </section>
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">Overall accuracy</div><div class="stat-value">${percent(accuracy)}</div><div class="stat-detail">${stats.correct} correct of ${stats.questions} questions</div></div>
      <div class="stat-card"><div class="stat-label">Study sessions</div><div class="stat-value">${stats.sessions}</div><div class="stat-detail">Saved privately on this device</div></div>
      <div class="stat-card"><div class="stat-label">Review cards due</div><div class="stat-value">${due}</div><div class="stat-detail">Recall before you reveal</div></div>
      <div class="stat-card"><div class="stat-label">Math drills</div><div class="stat-value">${stats.mathDrills.correct}/${stats.mathDrills.attempts}</div><div class="stat-detail">Correct in quick challenges</div></div>
    </div>
    <div class="grid-two">
      <div class="stack">${renderPlan()}
        <section class="card"><div class="card-heading"><div><h2>One week of consistency</h2><p>Sessions saved on this device.</p></div></div>${activity}</section>
      </div>
      <div class="stack">
        <section class="card"><div class="card-heading"><div><h2>Where to focus next</h2><p>Subjects adapt as you answer more questions.</p></div><button class="button small ghost" type="button" data-action="navigate" data-page="syllabus">Syllabus</button></div>
          ${weak.length ? renderSubjectRows(weak, 6) : `<div class="empty-state"><div class="empty-icon">✦</div><h2>Your coaching profile is building</h2><p>Start a few short sessions. The app will show areas to strengthen here without making guesses from just one answer.</p></div>`}
        </section>
        <section class="card"><div class="card-heading"><div><h2>Recent sessions</h2><p>Your last few saved practice results.</p></div></div>
          ${recent.length ? recent.map((session) => `<div class="history-item"><div><div class="history-title">${esc(getTrack(session.track)?.shortName || "Practice")} · ${session.count} questions</div><div class="history-detail">${dateLabel(session.date, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })} · ${session.correct} correct</div></div><span class="badge ${session.scorePct >= 70 ? "accent" : "gold"}">${percent(session.scorePct)}</span><span class="badge">${esc(session.mode === "mock" ? "Mock" : "Practice")}</span></div>`).join("") : `<p class="small-text muted">No sessions yet. Your results will show up here after your first quiz.</p>`}
        </section>
      </div>
    </div>
    <div class="disclaimer section-gap">Independent study aid; not affiliated with Kerala PSC or the Government of Kerala. Starter items are original practice questions, not official previous-year questions. Practice cannot guarantee selection. Check the current notification for the post you are applying for.</div>
  </div>`;
}

function renderPractice() {
  const track = getTrack();
  const domains = track.availableDomains || Object.keys(track.domainToBucket || {});
  const counts = currentCounts();
  const total = catalog.questions.length + profile.customQuestions.length + 30;
  return `<div class="page">${header("Practice studio", "Practice with purpose", "Switch between learn-as-you-go sessions and timed mock exams. Adaptive selection is local and uses your own results and review cards.")}
    <div class="practice-builder">
      <section class="card practice-options">
        <div class="card-heading"><div><h2>Build a session</h2><p>Choose a PSC level, subject focus and pace.</p></div></div>
        <form id="practice-form" class="stack">
          <div class="form-grid">
            <div class="field"><label for="practice-track">Exam track</label><select id="practice-track" name="track">${trackOptions()}</select></div>
            <div class="field"><label for="practice-domain">Subject</label><select id="practice-domain" name="domain"><option value="all">All subjects · syllabus mix</option>${domains.map((domain) => optionMarkup(domain, `${labelForDomain(domain)} (${counts[domain] || 0}${domain === "quantitative" ? "+ fresh drills" : ""})`, "")).join("")}</select></div>
          </div>
          <div class="form-grid">
            <div class="field"><label for="practice-count">Questions</label><select id="practice-count" name="count">${[10, 20, 50, 100].map((count) => optionMarkup(count, `${count} questions`, "10")).join("")}</select><span class="field-hint">If the selected bank is smaller, the app uses every available question without repeating.</span></div>
            <div class="field"><label for="practice-mode">Session type</label><select id="practice-mode" name="mode"><option value="practice">Learn as you go</option><option value="mock">Timed mock exam</option></select><span class="field-hint">Practice reveals explanations now. Mocks keep them hidden until submission.</span></div>
          </div>
          <label class="checkbox-row"><input type="checkbox" name="adaptive" checked><span><strong>Adapt the question mix</strong><br>Prioritise weaker topics and overdue review items as your history grows.</span></label>
          <label class="checkbox-row"><input type="checkbox" name="negative"${profile.settings.negativeMarking ? " checked" : ""}><span><strong>Use one-third negative marking in mocks</strong><br>Practice mode never subtracts marks. Empty answers are not penalised.</span></label>
          <button class="button primary" type="submit">Create my practice session <span aria-hidden="true">→</span></button>
        </form>
      </section>
      <div class="practice-start-card">
        <section class="card"><div class="eyebrow">Current blueprint</div><h2>${esc(track.name)}</h2><p class="card-subtitle">${esc(track.syllabusNote)}</p><div class="card-footer"><span class="badge accent">${track.durationMinutes} min · 100-mark outline</span><a class="button small ghost" href="${esc(track.officialUrl)}" target="_blank" rel="noreferrer">Official syllabus ↗</a></div></section>
        <section class="exam-mode"><strong>Local adaptive practice</strong><p>Your performance stays in this browser. Strong accuracy gradually increases challenge; repeated errors and due cards get more practice. This is a learning aid, not an exam prediction.</p></section>
        <div class="coverage-note">${catalog.questions.length} original starter questions are bundled, plus fresh locally generated aptitude drills. Current affairs are not bundled as live facts—import dated, source-linked questions in Syllabus &amp; Library.</div>
      </div>
    </div>
  </div>`;
}

function activeQuestion() {
  return quiz?.questions?.[quiz.current] || null;
}

function currentAnswer() {
  const question = activeQuestion();
  return question ? quiz.answers[question.id] || "" : "";
}

function clockText(seconds) {
  const minutes = Math.floor(Math.max(0, seconds) / 60);
  const remainder = Math.max(0, seconds) % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function feedbackMarkup(question) {
  const answer = quiz.answers[question.id];
  if (!answer || quiz.mode !== "practice") return "";
  const correct = answer === question.answer;
  const correctText = question.options[question.answer];
  return `<div class="feedback-box ${correct ? "correct-feedback" : "wrong-feedback"}" role="status" tabindex="-1"><strong>${correct ? "Correct — nice work." : `Not quite. The correct answer is ${esc(correctText)}.`}</strong>${question.explanation ? `<div style="margin-top:7px">${esc(question.explanation)}</div>` : ""}
    ${question.mnemonic ? `<div class="memory-hook"><b>Memory hook</b><span>${esc(question.mnemonic)}</span></div>` : ""}
    <div class="row" style="margin-top:11px"><button class="button small ghost" type="button" data-action="ask-about-question">Ask AI to explain this</button>${question.source_hint ? `<span class="small-text subtle">${esc(question.source_hint)}</span>` : ""}</div>
  </div>`;
}

function renderQuiz() {
  if (!quiz) return `<div class="page">${header("Practice studio", "No active session", "Start a practice set to begin.")}<button class="button primary" data-action="navigate" data-page="practice">Choose a session</button></div>`;
  const question = activeQuestion();
  if (!question) return "";
  const answer = currentAnswer();
  const answeredCount = Object.keys(quiz.answers).length;
  const progress = (quiz.current + 1) / quiz.questions.length * 100;
  const showFeedback = quiz.mode === "practice" && Boolean(answer);
  const currentHint = quiz.hints[question.id] ? question.mnemonic || "Try eliminating two options first. Identify the key word in the question before choosing." : "";
  const mock = quiz.mode === "mock";
  const options = ["A", "B", "C", "D"].map((letter) => {
    const correct = showFeedback && letter === question.answer;
    const incorrect = showFeedback && letter === answer && answer !== question.answer;
    return `<button type="button" class="answer-option${answer === letter ? " selected" : ""}${correct ? " correct" : ""}${incorrect ? " incorrect" : ""}" data-action="answer" data-letter="${letter}"${showFeedback ? " disabled" : ""} aria-pressed="${answer === letter}">
      <span class="answer-letter">${letter}</span><span>${esc(question.options[letter])}</span></button>`;
  }).join("");
  const map = quiz.questions.map((item, index) => `<button type="button" class="map-button${quiz.answers[item.id] ? " answered" : ""}${quiz.flags.has(item.id) ? " flagged" : ""}${quiz.current === index ? " current" : ""}" data-action="go-question" data-index="${index}" aria-label="Question ${index + 1}${quiz.answers[item.id] ? ", answered" : ", unanswered"}${quiz.flags.has(item.id) ? ", flagged" : ""}">${index + 1}</button>`).join("");
  return `<div class="page">
    <div class="quiz-toolbar"><div class="quiz-progress-meta"><button class="button small ghost" type="button" data-action="exit-quiz">← Exit</button><span>${esc(getTrack(quiz.trackId)?.shortName || "Practice")} · ${mock ? "Timed mock" : "Learn as you go"}</span><span>${answeredCount}/${quiz.questions.length} answered</span></div>
      <div class="row">${mock ? `<div class="quiz-clock" id="quiz-clock" aria-live="off">◷ ${clockText(quiz.remainingSeconds)}</div><button class="button small" type="button" data-action="finish-quiz">Submit mock</button>` : `<span class="badge accent">Practice · explanations on</span>`}</div>
    </div>
    <div class="progress-track" aria-label="Session progress"><span style="width:${progress}%"></span></div>
    <div class="quiz-container"><article class="question-card">
      <div class="question-meta"><span class="badge accent">${esc(labelForDomain(question.domain))}</span><span class="badge">${esc(question.topic || "General practice")}</span><span class="question-count">Question ${quiz.current + 1} of ${quiz.questions.length}</span></div>
      <h2 class="question-text" id="page-title">${esc(question.question)}</h2>
      <div class="answer-list">${options}</div>
      ${quiz.hints[question.id] ? `<div class="memory-hook" role="status" tabindex="-1"><b>Hint</b><span>${esc(currentHint)}</span></div>` : ""}
      ${feedbackMarkup(question)}
      <div class="question-actions"><div class="left-actions"><button class="button small ghost" type="button" data-action="hint"${answer ? " disabled" : ""}>Need a hint</button><button class="button small ghost" type="button" data-action="toggle-bookmark" data-qid="${esc(question.id)}">${profile.bookmarks.includes(question.id) ? "★ Saved" : "☆ Save"}</button>${mock ? `<button class="button small ghost" type="button" data-action="toggle-flag">${quiz.flags.has(question.id) ? "⚑ Flagged" : "⚐ Review later"}</button>` : ""}</div>
        <div class="right-actions"><button class="button small" type="button" data-action="previous-question"${quiz.current === 0 ? " disabled" : ""}>Previous</button>${quiz.current < quiz.questions.length - 1 ? `<button class="button small primary" type="button" data-action="next-question">Next question →</button>` : `<button class="button small primary" type="button" data-action="finish-quiz">Finish session</button>`}</div>
      </div>
    </article>
    <div class="between" style="margin-top:15px"><span class="small-text muted">Question map · flagged items have a gold underline</span><span class="small-text muted">${quiz.flags.size} flagged</span></div>
    <div class="question-map" aria-label="Question navigation">${map}</div>
    </div>
  </div>`;
}

function renderResults() {
  if (!lastResult) return `<div class="page">${header("Session complete", "Your progress is saved", "Your practice results stay on this device.")}<button class="button primary" data-action="navigate" data-page="practice">Start another session</button></div>`;
  const { result, session, quizSnapshot } = lastResult;
  const weak = Object.entries(result.byDomain).sort((a, b) => a[1].accuracyPct - b[1].accuracyPct);
  return `<div class="page">${header("Session complete", "Practice that turns into progress", "Review the reasoning now; missed and skipped questions have been added to your recall deck.")}
    <section class="results-hero"><div class="between"><div><div class="eyebrow">${esc(getTrack(session.track)?.name || "Practice")}</div><h2 style="margin:0;font-size:22px">${result.correct} correct · ${result.wrong} incorrect · ${result.skipped} skipped</h2><p class="muted small-text">${session.mode === "mock" ? `Timed mock · ${displayDuration(session.elapsedSeconds)} elapsed · ${profile.settings.negativeMarking ? "one-third negative marking applied" : "no negative marking"}` : `Learn-as-you-go · ${displayDuration(session.elapsedSeconds)} elapsed`} · ${result.attempted ? percent(result.accuracyPct) + " attempted accuracy" : "No answers attempted"}</p></div><div class="score-ring" aria-label="Score ${percent(result.scorePct)}">${percent(result.scorePct)}</div></div>
      <div class="hero-actions"><button class="button primary" type="button" data-action="navigate" data-page="practice">Practice again</button><button class="button" type="button" data-action="navigate" data-page="review">Review ${dueFlashcards(profile).length} due cards</button><button class="button ghost" type="button" data-action="navigate" data-page="ai">Ask your tutor</button></div></section>
    <div class="grid-two section-gap"><section class="card"><div class="card-heading"><div><h2>What to work on</h2><p>Based on this session's questions.</p></div></div>${renderSubjectRows(weak.map(([id, stats]) => ({ id, total: stats.total, accuracyPct: stats.accuracyPct })), 8)}</section><section class="card"><div class="card-heading"><div><h2>Next steps</h2><p>Build a useful follow-up routine.</p></div></div><div class="stack"><button class="button" type="button" data-action="retry-missed">Practice the missed topics</button><button class="button" type="button" data-action="navigate" data-page="review">Review the new flashcards</button><button class="button ghost" type="button" data-action="navigate" data-page="syllabus">Check syllabus coverage</button></div></section></div>
    <section class="section-gap"><div class="card-heading"><div><h2>Answer review</h2><p>Use the explanations as a small lesson, not just a score check.</p></div><span class="badge">${quizSnapshot.questions.length} questions</span></div>
      <div class="result-review">${result.reviews.map((review, index) => {
        const question = review.question;
        const selectedText = review.answered ? question.options[review.selected] : "No answer";
        const correctText = question.options[question.answer];
        return `<article class="review-row"><div class="between"><span class="badge ${review.correct ? "accent" : "gold"}">${review.correct ? "Correct" : review.answered ? "Review" : "Skipped"} · ${index + 1}</span><span class="badge">${esc(labelForDomain(question.domain))}</span></div><h3 style="margin-top:10px">${esc(question.question)}</h3><p>Your answer: ${esc(selectedText)} · Correct answer: <strong>${esc(correctText)}</strong></p>${question.explanation ? `<p>${esc(question.explanation)}</p>` : ""}${question.mnemonic ? `<div class="memory-hook"><b>Memory hook</b><span>${esc(question.mnemonic)}</span></div>` : ""}<div class="row" style="margin-top:9px"><button class="button small ghost" type="button" data-action="ask-about-review" data-review-index="${index}">Ask AI to explain</button>${profile.bookmarks.includes(question.id) ? `<span class="badge accent">Saved for later</span>` : ""}</div></article>`;
      }).join("")}</div>
    </section>
    <div class="disclaimer section-gap">Practice results reflect this local question set, not an official PSC score estimate or guarantee of selection.</div>
  </div>`;
}

function renderReview() {
  reviewQueue = reviewQueue.filter((id) => profile.flashcards.some((card) => card.id === id) && dueFlashcards(profile).some((card) => card.id === id));
  const due = dueFlashcards(profile);
  const card = reviewQueue.length ? profile.flashcards.find((item) => item.id === reviewQueue[0]) : null;
  return `<div class="page">${header("Spaced recall", "Flashcards that come back at the right time", "Try to retrieve the answer before revealing it. Your rating schedules the next review interval on this device.")}
    ${card ? `<div class="between"><span class="badge accent">${reviewQueue.length} due in this queue</span><span class="badge">${esc(labelForDomain(card.domain))}${card.topic ? ` · ${esc(card.topic)}` : ""}</span></div>
      <article class="flashcard section-gap"><div class="eyebrow">Recall first · then reveal</div><h2 class="flashcard-question">${esc(card.question)}</h2>
      ${reviewRevealed ? `<div class="flashcard-answer" tabindex="-1">${esc(card.answer)}</div>${card.explanation ? `<p class="flashcard-details">${esc(card.explanation)}</p>` : ""}${card.mnemonic ? `<div class="memory-hook"><b>Memory hook</b><span>${esc(card.mnemonic)}</span></div>` : ""}` : `<p class="muted small-text">Say or write your answer before tapping “Reveal answer”.</p>`}
      ${reviewRevealed ? "" : `<button class="button primary" type="button" data-action="reveal-card">Reveal answer</button>`}</article>
      ${reviewRevealed ? `<div class="section-gap"><div class="small-text muted" style="margin-bottom:8px">How well did you remember?</div><div class="rating-row"><button class="rating-button" type="button" data-action="rate-card" data-quality="again">Again<span>10 minutes</span></button><button class="rating-button" type="button" data-action="rate-card" data-quality="hard">Hard<span>1 day</span></button><button class="rating-button" type="button" data-action="rate-card" data-quality="good">Good<span>1–3 days</span></button><button class="rating-button" type="button" data-action="rate-card" data-quality="easy">Easy<span>4+ days</span></button></div></div>` : ""}
      <div class="row section-gap"><button class="button small ghost" type="button" data-action="skip-card">Skip this card for now</button><span class="small-text muted">${due.length} total due now · ${profile.flashcards.length} saved cards</span></div>`
      : `<section class="card empty-state"><div class="empty-icon">↻</div><h2>${due.length ? "Review queue complete" : "You're all caught up"}</h2><p>${due.length ? "You've reviewed the cards in this session. Come back to the remaining cards when they are due." : "Missed questions from your next quiz will become spaced-review flashcards. You can also save questions while practising."}</p><div class="row"><button class="button primary" type="button" data-action="navigate" data-page="practice">Start a practice set</button><button class="button" type="button" data-action="navigate" data-page="syllabus">View saved library</button></div></section>`}
    <section class="card section-gap"><div class="card-heading"><div><h2>Review queue</h2><p>A short daily review helps strengthen long-term recall.</p></div><span class="badge">${due.length} due</span></div>${due.slice(0, 6).map((item) => `<div class="history-item"><div><div class="history-title">${esc(item.topic || labelForDomain(item.domain))}</div><div class="history-detail">${esc(item.question).slice(0, 105)}${String(item.question).length > 105 ? "…" : ""}</div></div><span class="badge">${dateLabel(item.dueAt || item.next_review)}</span><span class="badge accent">Due</span></div>`).join("") || `<p class="small-text muted">Nothing else is due right now.</p>`}</section>
  </div>`;
}

function renderAI() {
  const provider = profile.settings.aiProvider;
  const providerName = AI_PROVIDERS[provider]?.label || "AI provider";
  const hasKey = Boolean(aiKey.trim());
  const safeHistory = aiHistory.slice(-10);
  const suggestions = [
    "Explain the difference between Fundamental Rights and Directive Principles simply.",
    "Teach me a quick method for solving percentage questions.",
    "Make a short memory hook for Kerala Renaissance reformers.",
    "Quiz me on the topic I find hardest, one question at a time.",
  ];
  return `<div class="page">${header("Optional AI tutor", "A tutor that adapts to your learning", "Ask for a simpler explanation, a step-by-step solution, a memory hook or a question-by-question quiz. Core practice never needs AI or an account.")}
    ${quiz ? `<div class="callout info" style="margin-bottom:14px">Your practice session is still open. <button class="button small" type="button" data-action="return-to-quiz">Return to question ${quiz.current + 1}</button></div>` : ""}
    <div class="callout warning"><strong>Privacy and cost, in plain language.</strong> Your prompt and a few recent messages from this tab's tutor conversation are sent directly from this browser to ${esc(providerName)} using your own API key. Nothing is routed through this app's server. Study-performance summaries are excluded unless you opt in below. Check the provider's privacy, data-retention and pricing terms; AI can be wrong, so verify exam facts with official sources.</div>
    <div class="grid-two section-gap">
      <section class="card"><div class="card-heading"><div><h2>Your AI setup</h2><p>The local adaptive coach works even when this is not configured.</p></div><span class="ai-key-status${hasKey ? " ready" : ""}">${hasKey ? "Key available" : "No key in memory"}</span></div>
        <div class="stack"><div class="field"><label>Provider</label><div class="small-text">${esc(providerName)} · ${esc(profile.settings.aiModel)}</div></div>
        ${hasKey ? `<div class="small-text muted">A key is present for this tab. It is ${rememberAIKey ? "remembered on this device because you opted in" : "held only in this tab's memory"}.</div>` : `<p class="small-text muted">Add your personal key in Settings to enable provider requests.</p>`}
        <button class="button" type="button" data-action="navigate" data-page="settings">Configure AI provider</button></div>
      </section>
      <section class="card"><div class="card-heading"><div><h2>Choose how you learn</h2><p>These preferences stay local and guide the tutor prompt.</p></div></div>
        <div class="form-grid"><div class="field"><label for="ai-language">Teaching language</label><select id="ai-language">${["English", "Malayalam", "Tamil", "Kannada"].map((language) => optionMarkup(language, language, profile.settings.teachingLanguage)).join("")}</select></div><div class="field"><label for="ai-style">Teaching style</label><select id="ai-style">${[["step-by-step", "Step by step"], ["examples-first", "Examples first"], ["quiz-me", "Ask me questions"], ["memory-hooks", "Memory tricks"]].map(([id, label]) => optionMarkup(id, label, profile.settings.teachingStyle)).join("")}</select></div></div>
        <label class="checkbox-row section-gap"><input type="checkbox" id="include-learning-profile"${profile.settings.includeLearningProfile ? " checked" : ""}><span><strong>Include a minimal study summary when I ask</strong><br>Shares only my exam track, learning preferences, streak, due-card count, subject accuracy and repeated difficult topics. No name, contact details or full answer history.</span></label>
      </section>
    </div>
    <section class="card section-gap ai-chat" aria-live="polite"><div class="between"><div><h2>Tutor conversation</h2><p class="card-subtitle">This conversation is kept in memory for this tab only; it is not included in your study backup.</p></div>${safeHistory.length ? `<button class="button small ghost" type="button" data-action="clear-ai-chat">Clear chat</button>` : ""}</div>
      <div class="ai-thread">${safeHistory.length ? safeHistory.map((entry) => `<div class="chat-bubble ${entry.role === "assistant" ? "assistant" : "user"}"><span class="chat-label">${entry.role === "assistant" ? "Tutor" : "You"}</span>${esc(entry.content)}</div>`).join("") : `<div class="empty-state"><div class="empty-icon">✦</div><h2>What are you working on?</h2><p>Start with a topic, a question you missed, or the kind of explanation that helps you remember.</p></div>`}${aiBusy ? `<div class="chat-bubble assistant" role="status">Thinking through a clear explanation…</div>` : ""}</div>
      <form id="ai-form" class="ai-composer"><textarea name="prompt" id="ai-prompt" maxlength="6000" placeholder="Ask for a clear explanation, a hint, a worked maths solution or a short quiz…" required>${esc(aiPrefill)}</textarea>
        <div class="choice-pills">${suggestions.map((prompt) => `<button class="button small ghost" type="button" data-action="ai-suggestion" data-prompt="${esc(prompt)}">${esc(prompt.length > 44 ? prompt.slice(0, 41) + "…" : prompt)}</button>`).join("")}</div>
        <label class="checkbox-row"><input type="checkbox" name="ai-consent" required><span>I approve sending this prompt and recent chat context to ${esc(providerName)} using my own key. I will not include personal or sensitive information.${profile.settings.includeLearningProfile ? " The optional minimal study summary will also be sent." : ""}</span></label>
        <div class="ai-composer-actions"><span class="ai-response-meta">${aiBusy ? "Waiting for the provider…" : aiUsageLabel ? esc(aiUsageLabel) : "One request is sent only after you press Send."}</span><button class="button primary" type="submit"${aiBusy || !hasKey ? " disabled" : ""}>${aiBusy ? "Thinking…" : "Send to tutor ↗"}</button></div>
      </form>
    </section>
    <div class="disclaimer section-gap">AI-generated explanations and quizzes may contain errors and are not official PSC guidance. Verify dates, current affairs, syllabus changes and legal facts against Kerala PSC or another primary source.</div>
  </div>`;
}

function mathField(field, currentKind) {
  const required = currentKind !== "speed_distance_time" || field.id !== currentMathTarget;
  if (field.type === "select") return `<div class="field"><label for="calc-${field.id}">${esc(field.label)}</label><select id="calc-${field.id}" name="${esc(field.id)}">${field.options.map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join("")}</select></div>`;
  return `<div class="field"><label for="calc-${field.id}">${esc(field.label)}</label><input id="calc-${field.id}" name="${esc(field.id)}" type="${field.type || "text"}" inputmode="${field.type === "text" ? "text" : "decimal"}" autocomplete="off" placeholder="${esc(field.placeholder || "Enter a value")}"${required ? " required" : ""}></div>`;
}

function renderMathResult() {
  if (!currentMathResult) return "";
  return `<div class="math-result" role="status"><div class="eyebrow">Worked solution</div><div class="math-result-value">${esc(currentMathResult.title)} ${esc(currentMathResult.value)}${currentMathResult.unit ? ` ${esc(currentMathResult.unit)}` : ""}</div><ol class="math-steps">${currentMathResult.steps.map((step) => `<li>${esc(step)}</li>`).join("")}</ol><div class="memory-hook"><b>Remember</b><span>${esc(currentMathResult.memory)}</span></div></div>`;
}

function renderMathDrill() {
  const stats = profile.stats.mathDrills;
  if (!currentMathDrill) return `<section class="card"><div class="card-heading"><div><h2>One-minute mental maths</h2><p>Fresh offline questions, instant worked steps and a small streak.</p></div><span class="badge accent">${stats.correct}/${stats.attempts} correct</span></div><div class="empty-state"><div class="empty-icon">∑</div><h2>Warm up your recall</h2><p>Try to estimate before you calculate. No timer and no penalty for a wrong answer.</p><button class="button primary" type="button" data-action="new-math-drill">Generate a challenge</button></div></section>`;
  return `<section class="card"><div class="card-heading"><div><h2>One-minute mental maths</h2><p>Fresh offline question · ${stats.streak} correct in a row</p></div><span class="badge accent">${stats.correct}/${stats.attempts} correct</span></div>
    <div class="drill-prompt" style="margin:15px 0">${esc(currentMathDrill.prompt)}</div>
    ${mathDrillResult ? `<div class="feedback-box ${mathDrillResult.correct ? "correct-feedback" : "wrong-feedback"}" role="status"><strong>${mathDrillResult.correct ? "Correct — great recall." : `The answer is ${formatMathNumber(currentMathDrill.answer)}.`}</strong><ol class="math-steps" style="margin-top:9px">${currentMathDrill.steps.map((step) => `<li>${esc(step)}</li>`).join("")}</ol><div class="memory-hook"><b>Memory hook</b><span>${esc(currentMathDrill.memory)}</span></div></div><button class="button primary" style="margin-top:13px" type="button" data-action="new-math-drill">Try another</button>` : `<form id="math-drill-form" class="row"><label class="field" style="flex:1"><span class="field-label">Your answer</span><input name="answer" type="text" inputmode="decimal" autocomplete="off" placeholder="Estimate, then calculate" required></label><button class="button primary" type="submit" style="align-self:end">Check answer</button></form>`}
  </section>`;
}

function renderMathLab() {
  const kind = currentMathKind;
  const configuration = MATH_CALCULATORS[kind] || MATH_CALCULATORS.percent_of;
  return `<div class="page">${header("Math Lab", "Understand the steps, not just the answer", "Twelve friendly calculators show the formula, each substitution and a short memory cue. Everything runs offline in your browser.")}
    <div class="calculator-layout">
      <section class="card"><div class="card-heading"><div><h2>Guided calculator</h2><p>Enter the known values; the target selector lets you solve any one side.</p></div></div>
        <form id="math-calculator-form" class="calculator-form">
          <div class="field"><label for="calculator-kind">Choose a tool</label><select id="calculator-kind" name="kind">${Object.entries(MATH_CALCULATORS).map(([id, calculator]) => optionMarkup(id, calculator.title, kind)).join("")}</select></div>
          ${kind === "speed_distance_time" ? `<div class="field"><label for="calc-target">Find</label><select id="calc-target" name="target">${[["distance", "Distance"], ["speed", "Speed"], ["time", "Time"]].map(([id, label]) => optionMarkup(id, label, currentMathTarget)).join("")}</select><span class="field-hint">Leave the target's input empty; enter the other two.</span></div>` : ""}
          <div class="form-grid">${configuration.fields.map((field) => mathField(field, kind)).join("")}</div>
          <button class="button primary" type="submit">Show the steps</button>
        </form>${renderMathResult()}
      </section>
      <div class="stack">
        <section class="card"><div class="card-heading"><div><h2>Formula memory board</h2><p>Quick recall cues for common PSC arithmetic.</p></div></div>
          <div class="memory-list">
            ${[["Percent", "10% = ÷10 · 5% = half of 10% · 1% = ÷100"], ["Average", "Average × count = total"], ["Simple interest", "P × R × T ÷ 100"], ["Distance", "Distance = speed × time"], ["Time & work", "Add one-day work rates; invert the total"], ["Ratio", "Add parts → one part → required share"], ["Rectangle", "Area = length × width · perimeter = 2(length + width)"], ["Fraction", "Divide numerator by denominator, then ×100 for %"]].map(([term, cue]) => `<div class="memory-row"><strong>${esc(term)}</strong><span>${esc(cue)}</span></div>`).join("")}
          </div>
        </section>${renderMathDrill()}
      </div>
    </div>
  </div>`;
}

function renderSyllabus() {
  const track = getTrack();
  const counts = currentCounts();
  const weak = Object.fromEntries(weakDomains(profile, 0).map((entry) => [entry.id, entry]));
  const trackDomains = track.availableDomains || Object.keys(track.domainToBucket || {});
  const bucketRows = Object.entries(track.weights).map(([bucket, marks]) => {
    const domains = trackDomains.filter((domain) => track.domainToBucket?.[domain] === bucket);
    return `<tr><td><strong>${esc(track.bucketLabels[bucket] || bucket)}</strong><div class="field-hint">${domains.map((domain) => esc(labelForDomain(domain))).join(" · ") || "No matching offline items yet"}</div></td><td>${marks}/100</td><td>${domains.reduce((sum, domain) => sum + (counts[domain] || 0), 0)}</td></tr>`;
  }).join("");
  const supplementary = trackDomains.filter((domain) => !track.domainToBucket?.[domain]);
  const domainRows = trackDomains.map((domain) => {
    const performance = weak[domain];
    return `<tr><td>${esc(labelForDomain(domain))}${supplementary.includes(domain) ? ` <span class="badge">Supplementary</span>` : ""}</td><td>${counts[domain] || 0}</td><td>${performance ? percent(performance.accuracyPct) : "Not enough attempts"}</td><td>${performance?.total || 0}</td></tr>`;
  }).join("");
  const currentAffairsCount = counts.current_affairs || 0;
  return `<div class="page">${header("Syllabus & question library", "Study the syllabus, not just a question list", "Choose your exam track to see its linked common preliminary blueprint, available practice items and your local progress. Post-specific notifications can differ.")}
    <section class="card"><div class="between"><div><div class="eyebrow">Exam track</div><h2>${esc(track.name)}</h2><p class="card-subtitle">${esc(track.syllabusNote)}</p></div><div class="field" style="min-width:190px"><label for="syllabus-track">Change track</label><select id="syllabus-track">${trackOptions()}</select></div></div>
      <div class="table-wrap section-gap"><table class="data-table"><thead><tr><th>Blueprint section</th><th>Weight</th><th>Available practice</th></tr></thead><tbody>${bucketRows}</tbody></table></div>
      <div class="card-footer"><a class="button small" href="${esc(track.officialUrl)}" target="_blank" rel="noreferrer">Open official syllabus ↗</a></div>
    </section>
    <section class="card section-gap"><div class="card-heading"><div><h2>Question-bank coverage</h2><p>${catalog.questions.length} original offline starters + ${profile.customQuestions.length} imported questions.</p></div></div>
      <div class="table-wrap"><table class="data-table"><thead><tr><th>Subject</th><th>Questions</th><th>Accuracy</th><th>Attempts</th></tr></thead><tbody>${domainRows}</tbody></table></div>
      ${currentAffairsCount ? `<div class="callout success section-gap">${currentAffairsCount} dated, source-linked current-affairs question(s) are in your library. Check their publication dates before relying on them.</div>` : `<div class="callout warning section-gap"><strong>Current affairs are not bundled.</strong> Add fresh questions with a publisher and publication date. Static starter questions are deliberately not described as current.</div>`}
    </section>
    <section class="card section-gap"><div class="card-heading"><div><h2>Your own question packs</h2><p>Import a teacher's or study group's original questions. JSON is validated locally and never executes code.</p></div></div>
      <div class="row"><button class="button primary" type="button" data-action="import-pack">Import question pack (JSON)</button><button class="button" type="button" data-action="download-template">Download question template</button><button class="button ghost" type="button" data-action="practice-bookmarks">Practice saved questions (${profile.bookmarks.length})</button></div>
      <p class="small-text muted section-gap">Supported subjects include Kerala and Indian history, geography, civics, economy, constitution, science, computer basics, current affairs, aptitude, English and Malayalam, Tamil or Kannada. Current-affairs items need a dated source hint.</p>
      <input id="question-pack-file" type="file" accept="application/json,.json" class="hidden" aria-label="Choose JSON question pack">
    </section>
  </div>`;
}

function renderProgress() {
  const total = profile.stats.questions;
  const overall = total ? profile.stats.correct / total * 100 : 0;
  const areas = weakDomains(profile, 0).sort((left, right) => right.total - left.total);
  const sessions = [...profile.sessions].reverse();
  const streak = profile.stats.streak;
  const daily = createDailyPlan(profile, catalog.tracks);
  const checkCount = Object.values(profile.dailyChecks[localDateKey()] || {}).filter(Boolean).length;
  return `<div class="page">${header("Progress & reflection", "See how your preparation is changing", "These indicators come from your local practice sessions. They are useful for planning, not an official pass or rank prediction.")}
    <div class="stats-grid"><div class="stat-card"><div class="stat-label">Answered correctly</div><div class="stat-value">${profile.stats.correct}</div><div class="stat-detail">of ${total} practice questions</div></div><div class="stat-card"><div class="stat-label">Overall score rate</div><div class="stat-value">${percent(overall)}</div><div class="stat-detail">Includes skipped items in denominator</div></div><div class="stat-card"><div class="stat-label">Current streak</div><div class="stat-value">${streak} days</div><div class="stat-detail">Consecutive days with a session</div></div><div class="stat-card"><div class="stat-label">Today's plan</div><div class="stat-value">${checkCount}/${daily.length}</div><div class="stat-detail">Study checklist items complete</div></div></div>
    <div class="grid-two"><section class="card"><div class="card-heading"><div><h2>Subject accuracy</h2><p>Small samples are shown, but adaptive focus waits for three questions.</p></div></div>${renderSubjectRows(areas, 16)}</section><section class="card"><div class="card-heading"><div><h2>Recent activity</h2><p>Most recent saved sessions on this browser.</p></div></div>${sessions.length ? sessions.slice(0, 25).map((session) => `<div class="history-item"><div><div class="history-title">${esc(getTrack(session.track)?.shortName || "Practice")} · ${esc(session.mode === "mock" ? "Timed mock" : "Practice")}</div><div class="history-detail">${dateLabel(session.date, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })} · ${session.correct} correct of ${session.count}</div></div><span class="badge ${session.scorePct >= 70 ? "accent" : "gold"}">${percent(session.scorePct)}</span><span class="badge">${displayDuration(session.elapsedSeconds)}</span></div>`).join("") : `<div class="empty-state"><div class="empty-icon">⌁</div><h2>Your timeline starts here</h2><p>Finish a short session to see your first progress point.</p><button class="button primary" type="button" data-action="navigate" data-page="practice">Start practice</button></div>`}</section></div>
    <div class="callout info section-gap"><strong>Adaptive next step:</strong> Your question mix uses subject accuracy, repeated errors and due flashcards. It doesn't infer personal traits or share behavior with a provider unless you opt in for an AI request.</div>
  </div>`;
}

function renderSettings() {
  const provider = profile.settings.aiProvider;
  const model = profile.settings.aiModel;
  const hasRememberedKey = Boolean(rememberAIKey && aiKey);
  return `<div class="page">${header("Settings & privacy", "Your device, your settings", "The app is designed to work offline. Export a backup if you want to move your study profile between devices.")}
    <div class="grid-two">
      <section class="card"><div class="card-heading"><div><h2>Study preferences</h2><p>These choices adjust practice and coaching style.</p></div></div>
        <div class="stack section-gap">
          <div class="field"><label for="setting-track">Default exam track</label><select id="setting-track">${trackOptions()}</select></div>
          <div class="form-grid"><div class="field"><label for="daily-goal">Daily study goal</label><select id="daily-goal">${[15, 30, 45, 60, 90, 120].map((minutes) => optionMarkup(minutes, `${minutes} minutes`, String(profile.settings.dailyGoalMinutes))).join("")}</select></div><div class="field"><label for="theme-setting">Appearance</label><select id="theme-setting">${[["dark", "Dark"], ["light", "Light"], ["system", "Use device setting"]].map(([id, label]) => optionMarkup(id, label, profile.settings.theme)).join("")}</select></div></div>
          <div class="field"><label for="setting-language">AI teaching language</label><select id="setting-language">${["English", "Malayalam", "Tamil", "Kannada"].map((language) => optionMarkup(language, language, profile.settings.teachingLanguage)).join("")}</select><span class="field-hint">Only the optional AI explanation is translated; question text remains as supplied.</span></div>
          <div class="field"><label for="setting-style">Preferred explanation style</label><select id="setting-style">${[["step-by-step", "Step by step"], ["examples-first", "Examples first"], ["quiz-me", "Ask me questions"], ["memory-hooks", "Memory tricks" ]].map(([id, label]) => optionMarkup(id, label, profile.settings.teachingStyle)).join("")}</select></div>
          <label class="checkbox-row"><input id="negative-setting" type="checkbox"${profile.settings.negativeMarking ? " checked" : ""}><span><strong>Default one-third negative marking for mock exams</strong><br>You can change this per practice set.</span></label>
        </div>
      </section>
      <section class="card"><div class="card-heading"><div><h2>Optional AI provider</h2><p>Bring your own personal API key. Local practice remains free of AI calls.</p></div></div>
        <div class="stack section-gap">
          <div class="field"><label for="ai-provider">Provider</label><select id="ai-provider">${Object.entries(AI_PROVIDERS).map(([id, details]) => optionMarkup(id, details.label, provider)).join("")}</select><span class="field-hint">${esc(AI_PROVIDERS[provider].keyHelp)} <a href="${esc(AI_PROVIDERS[provider].keyUrl)}" target="_blank" rel="noreferrer">Open provider key settings ↗</a></span></div>
          <div class="field"><label for="ai-model">Model ID</label><input id="ai-model" type="text" value="${esc(model)}" maxlength="120" autocomplete="off" spellcheck="false"><span class="field-hint">Default models can change. Check the provider's current model list and pricing before use.</span></div>
          <div class="field"><label for="ai-key">Your API key</label><input id="ai-key" type="password" value="${esc(aiKey)}" autocomplete="new-password" spellcheck="false" maxlength="512" placeholder="Paste your personal provider key"><span class="field-hint">Sent only to the selected provider over HTTPS, directly from this browser. Never add the key to a question pack or backup file.</span></div>
          <label class="checkbox-row"><input id="remember-ai-key" type="checkbox"${rememberAIKey ? " checked" : ""}><span><strong>Remember this key on this device</strong><br>Off by default. Device storage is not a secure vault; anyone with access to this browser profile may be able to use it.${hasRememberedKey && rememberAIKey ? " A key is currently stored on this device." : ""}</span></label>
          <div class="row"><button class="button" type="button" data-action="clear-ai-key">Forget API key</button><span class="ai-key-status${aiKey ? " ready" : ""}">${aiKey ? "Available in this tab" : "Not configured"}</span></div>
          <div class="callout warning"><strong>Keep control of cost and data.</strong> Create a key with provider-side limits if available. Each AI answer uses your provider account. No app-wide key is embedded in this project.</div>
        </div>
      </section>
    </div>
    <section class="card section-gap"><div class="card-heading"><div><h2>Move or back up your profile</h2><p>Your questions, progress, bookmarks and review cards stay in browser storage until you export them.</p></div></div>
      <div class="row"><button class="button primary" type="button" data-action="export-backup">Export profile backup</button><button class="button" type="button" data-action="import-backup">Import/restore backup</button><button class="button" type="button" data-action="export-csv">Export flashcards (CSV)</button></div>
      <p class="small-text muted section-gap">Backups never contain your AI API key or tutor conversation. Imports support PWA backups and the desktop app's JSON profile backup. Store the file somewhere private.</p>
      <input id="backup-file" type="file" accept="application/json,.json" class="hidden" aria-label="Choose profile backup">
    </section>
    <section class="card section-gap"><div class="card-heading"><div><h2>Platform support</h2><p>Install this progressive web app from a secure HTTPS address and keep studying offline.</p></div></div>
      <div class="grid-three"><div class="exam-mode"><strong>Windows · macOS · Linux</strong><p>Use a recent Chrome, Edge, Firefox or Safari browser. Add the site as an app/shortcut where supported, or keep it pinned in a tab.</p></div><div class="exam-mode"><strong>Android</strong><p>Open the secure site in Chrome or another supported browser and choose Install app or Add to Home screen.</p></div><div class="exam-mode"><strong>iPhone · iPad</strong><p>Open in Safari, tap Share, then Add to Home Screen. Safari may not show a native install prompt.</p></div></div>
      <div class="callout info section-gap">A PWA uses separate local storage on each browser/device; it does not silently sync. Export and import a backup to move progress. Installable offline caching requires HTTPS (or localhost during development).</div>
    </section>
    <section class="card section-gap"><div class="card-heading"><div><h2>Local data controls</h2><p>No sign-in, trackers, ad SDKs or automatic cloud backup.</p></div></div><p class="small-text muted">Saved profile size: approximately ${Math.max(1, Math.round(new Blob([JSON.stringify(profile)]).size / 1024))} KB in this browser. Clearing site data in your browser also removes this profile.</p><button class="button danger" type="button" data-action="reset-profile">Delete local progress and imported questions</button></section>
    <div class="disclaimer section-gap">Independent educational software, not a Kerala PSC or government service. AI use is optional and governed by your chosen provider's terms.</div>
  </div>`;
}

function renderSyllabusAndEtc() {
  return "";
}

function flashcardCsv() {
  const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const rows = [["Question", "Answer", "Explanation", "Memory hook", "Subject", "Topic", "Next review"]];
  for (const card of profile.flashcards) rows.push([card.question, card.answer, card.explanation, card.mnemonic, labelForDomain(card.domain), card.topic, card.dueAt || card.next_review].map(quote));
  return rows.map((row) => row.map((cell) => typeof cell === "string" && cell.startsWith('"') ? cell : quote(cell)).join(",")).join("\r\n");
}

function downloadFile(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function createQuestionPackTemplate() {
  const template = {
    version: 1,
    questions: [{
      id: "my-original-question-001",
      domain: "history",
      topic: "Kerala Renaissance",
      question: "Write an original multiple-choice question.",
      options: { A: "Option one", B: "Option two", C: "Option three", D: "Option four" },
      answer: "B",
      explanation: "Explain why the answer is correct in plain language.",
      mnemonic: "Optional memory hook or acronym.",
      source_hint: "Publisher or book; include publication date for current affairs.",
    }],
  };
  downloadFile("kerala-psc-question-pack-template.json", JSON.stringify(template, null, 2), "application/json");
}

function allQuestions() {
  return [...catalog.questions, ...profile.customQuestions];
}

function startPractice(options = {}) {
  const form = document.querySelector("#practice-form");
  const data = options.formData || (form ? new FormData(form) : null);
  const trackId = options.trackId || data?.get("track") || profile.settings.track;
  const domain = options.domain || data?.get("domain") || "all";
  const requested = Number.parseInt(options.count || data?.get("count") || "10", 10);
  const mode = options.mode || data?.get("mode") || "practice";
  const adaptive = options.adaptive ?? (data ? data.get("adaptive") === "on" : true);
  const pool = [...allQuestions(), ...generateAptitudeQuestions(36)];
  let questionSource = pool;
  if (options.bookmarksOnly) {
    const bookmarks = new Set(profile.bookmarks);
    questionSource = pool.filter((question) => bookmarks.has(question.id));
  }
  let questions;
  try {
    questions = selectPracticeQuestions(questionSource, {
      trackId, tracks: catalog.tracks, count: requested, domain, profile, adaptive,
    });
  } catch (error) {
    toast(error.message, "error");
    return;
  }
  if (!questions.length) {
    toast("No saved questions are available in this selection yet.", "error");
    return;
  }
  const track = getTrack(trackId);
  const timeLimitSeconds = mode === "mock" ? Math.max(5, Math.ceil(track.durationMinutes * questions.length / 100)) * 60 : 0;
  const negative = data ? data.get("negative") === "on" : profile.settings.negativeMarking;
  profile.settings.track = trackId;
  profile.settings.negativeMarking = Boolean(negative);
  save();
  lastResult = null;
  quiz = {
    questions,
    answers: {},
    flags: new Set(),
    hints: {},
    questionTimes: {},
    mode,
    trackId,
    adaptive,
    negative,
    current: 0,
    startedAt: Date.now(),
    enteredAt: Date.now(),
    timeLimitSeconds,
    remainingSeconds: timeLimitSeconds,
  };
  reviewQueue = [];
  currentPage = "quiz";
  render();
  if (mode === "mock") startQuizTimer();
  if (questions.length < requested) toast(`Using ${questions.length} available question(s); no questions are repeated.`, "info");
  document.querySelector("#main-content")?.focus({ preventScroll: true });
}

function trackQuestionTime() {
  if (!quiz) return;
  const question = activeQuestion();
  if (!question) return;
  const now = Date.now();
  const elapsed = Math.max(0, (now - quiz.enteredAt) / 1000);
  quiz.questionTimes[question.id] = (quiz.questionTimes[question.id] || 0) + elapsed;
  quiz.enteredAt = now;
}

function startQuizTimer() {
  clearInterval(quizTimer);
  quizTimer = setInterval(() => {
    if (!quiz || currentPage !== "quiz") return;
    quiz.remainingSeconds = Math.max(0, quiz.remainingSeconds - 1);
    refreshClockView();
    if (quiz.remainingSeconds <= 0) finishQuiz(true);
  }, 1000);
}

function refreshClockView() {
  const clock = document.querySelector("#quiz-clock");
  if (!clock || !quiz) return;
  clock.textContent = `◷ ${clockText(quiz.remainingSeconds)}`;
  clock.classList.toggle("urgent", quiz.remainingSeconds <= 60);
}

function selectQuestion(index) {
  if (!quiz || index < 0 || index >= quiz.questions.length || index === quiz.current) return;
  trackQuestionTime();
  quiz.current = index;
  render();
}

function chooseAnswer(letter) {
  if (!quiz || !["A", "B", "C", "D"].includes(letter)) return;
  const question = activeQuestion();
  if (quiz.mode === "practice" && quiz.answers[question.id]) return;
  trackQuestionTime();
  quiz.answers[question.id] = letter;
  render();
}

function finishQuiz(automatic = false) {
  if (!quiz) return;
  const unanswered = quiz.questions.length - Object.keys(quiz.answers).length;
  if (!automatic && quiz.mode === "mock" && unanswered > 0) {
    const shouldSubmit = window.confirm(`There ${unanswered === 1 ? "is" : "are"} ${unanswered} unanswered question${unanswered === 1 ? "" : "s"}. Submit the mock now?`);
    if (!shouldSubmit) return;
  }
  trackQuestionTime();
  clearInterval(quizTimer);
  quizTimer = null;
  const ended = Date.now();
  const elapsedSeconds = Math.max(0, Math.round((ended - quiz.startedAt) / 1000));
  const snapshot = {
    ...quiz,
    questions: [...quiz.questions],
    answers: { ...quiz.answers },
    flags: [...quiz.flags],
    hints: { ...quiz.hints },
    questionTimes: { ...quiz.questionTimes },
    elapsedSeconds,
  };
  const update = recordSession(profile, snapshot, { penalty: quiz.mode === "mock" && quiz.negative ? 1 / 3 : 0, now: new Date(ended) });
  profile = update.profile;
  lastResult = { result: update.result, session: update.session, quizSnapshot: snapshot };
  quiz = null;
  reviewQueue = [];
  save();
  currentPage = "results";
  render();
  toast(automatic ? "Time is up. Your mock exam has been submitted." : "Session saved. Missed questions are now in your recall deck.", "success");
}

function toggleBookmark(questionId) {
  const index = profile.bookmarks.indexOf(questionId);
  if (index >= 0) profile.bookmarks.splice(index, 1);
  else profile.bookmarks.push(questionId);
  save();
  render();
}

function openAIWithPrompt(prompt) {
  aiPrefill = prompt;
  currentPage = "ai";
  render();
  document.querySelector("#ai-prompt")?.focus();
}

function askAboutCurrentQuestion() {
  const question = activeQuestion();
  if (!question) return;
  const selectedAnswer = quiz.answers[question.id];
  const myAnswer = selectedAnswer ? question.options[selectedAnswer] : "Not answered";
  const correctAnswer = question.options[question.answer];
  const prompt = `Please explain this practice question in ${profile.settings.teachingLanguage} using my preferred ${profile.settings.teachingStyle} style.\n\nQuestion: ${question.question}\nOptions: ${Object.entries(question.options).map(([letter, option]) => `${letter}. ${option}`).join("; ")}\nMy answer: ${myAnswer}\nAnswer shown by this study pack: ${correctAnswer}\nPack explanation: ${question.explanation || "No explanation was supplied."}\n\nExplain the reasoning, point out a useful memory cue, and tell me if any claim needs an official source check.`;
  openAIWithPrompt(prompt);
}

function askAboutReview(index) {
  const review = lastResult?.result?.reviews?.[index];
  if (!review) return;
  openAIWithPrompt(`Please teach me this question in ${profile.settings.teachingLanguage} using a ${profile.settings.teachingStyle} approach.\n\nQuestion: ${review.question.question}\nCorrect answer: ${review.question.options[review.question.answer]}\nMy answer: ${review.answered ? review.question.options[review.selected] : "I skipped it"}\nPack explanation: ${review.question.explanation || "No explanation supplied."}\n\nShow the reasoning clearly and offer one memory hook.`);
}

async function sendAIRequest(form) {
  if (aiBusy) return;
  const formData = new FormData(form);
  const prompt = String(formData.get("prompt") || "").trim();
  if (!formData.has("ai-consent")) {
    toast("Please confirm this request may be sent to your selected AI provider.", "error");
    return;
  }
  if (!aiKey.trim()) {
    toast("Add your personal provider key in Settings to enable AI tutoring.", "error");
    return;
  }
  const previous = [...aiHistory];
  const provider = profile.settings.aiProvider;
  const trackName = getTrack().name;
  const systemPrompt = buildTutorSystemPrompt({
    profile,
    includeLearningProfile: profile.settings.includeLearningProfile,
    domains: catalog.domains,
    trackName,
  });
  aiBusy = true;
  aiPrefill = "";
  render();
  try {
    const answer = await askTutor({
      provider,
      model: profile.settings.aiModel,
      apiKey: aiKey,
      prompt,
      history: previous,
      systemPrompt,
    });
    aiHistory = [...previous, { role: "user", content: prompt }, { role: "assistant", content: answer.text }].slice(-12);
    profile.stats.aiCalls += 1;
    save();
    const usage = answer.usage?.totalTokenCount || answer.usage?.total_tokens;
    aiUsageLabel = `Answered by ${answer.model}${usage ? ` · ${usage} provider tokens` : ""}. Verify facts with official sources.`;
    toast("Your tutor response is ready.", "success");
  } catch (error) {
    aiHistory = [...previous, { role: "user", content: prompt }, { role: "assistant", content: `I couldn't reach the selected provider. ${error.message}\n\nYour local practice and progress are unaffected. Check your connection, key, model and provider limits in Settings.` }].slice(-12);
    toast(error.message, "error");
  } finally {
    aiBusy = false;
    currentPage = "ai";
    render();
    document.querySelector("#ai-prompt")?.focus();
  }
}

function updateAIKey(value) {
  aiKey = String(value || "").trim();
  if (!rememberAIKey) return;
  try {
    if (aiKey) localStorage.setItem(AI_KEY_STORAGE_KEY, aiKey);
    else localStorage.removeItem(AI_KEY_STORAGE_KEY);
  } catch {
    rememberAIKey = false;
    toast("This browser cannot store the key persistently. It will only remain in this tab.", "error");
  }
}

function startReviewQueue() {
  reviewQueue = dueFlashcards(profile).map((card) => card.id);
  reviewRevealed = false;
  currentPage = "review";
  render();
}

function rateCurrentCard(quality) {
  const cardId = reviewQueue[0];
  if (!cardId) return;
  try {
    profile = scheduleFlashcard(profile, cardId, quality);
    reviewQueue.shift();
    reviewRevealed = false;
    save();
    render();
    toast("Review saved. Your next interval has been scheduled.", "success");
  } catch (error) {
    toast(error.message, "error");
  }
}

function startMathDrill() {
  currentMathDrill = generateMathDrill();
  mathDrillResult = null;
  render();
}

function checkMathDrill(form) {
  if (!currentMathDrill || mathDrillResult) return;
  const raw = new FormData(form).get("answer");
  const correct = mathAnswerMatches(raw, currentMathDrill.answer, currentMathDrill.tolerance);
  mathDrillResult = { correct };
  profile.stats.mathDrills.attempts += 1;
  if (correct) {
    profile.stats.mathDrills.correct += 1;
    profile.stats.mathDrills.streak += 1;
  } else {
    profile.stats.mathDrills.streak = 0;
  }
  save();
  render();
}

function setPage(page) {
  if (page === "quiz" && !quiz) page = "practice";
  if (page === "results" && !lastResult) page = "home";
  if (quiz && page === "ai" && quiz.mode === "mock") {
    if (!window.confirm("AI tutoring is turned off during a timed mock. Leave and discard this unfinished mock?")) return;
    clearInterval(quizTimer);
    quizTimer = null;
    quiz = null;
  } else if (quiz && currentPage === "quiz" && page !== "quiz" && page !== "ai") {
    if (!window.confirm("Leave this session? Its unfinished answers will not be scored or saved.")) return;
    clearInterval(quizTimer);
    quizTimer = null;
    quiz = null;
  } else if (quiz && currentPage === "ai" && page !== "quiz" && page !== "ai") {
    if (!window.confirm("Leave this unfinished practice session? Its answers will not be scored or saved.")) return;
    quiz = null;
  }
  if (page === "review") startReviewQueue();
  else {
    currentPage = page;
    render();
  }
  document.getElementById("main-content")?.focus({ preventScroll: true });
}

function getImportProfile(raw) {
  return importProfileBackup(raw);
}

function importBackupFile(file) {
  if (!file) return;
  if (file.size > 25 * 1024 * 1024) {
    toast("Backup files must be 25 MB or smaller.", "error");
    return;
  }
  file.text().then((text) => {
    const raw = JSON.parse(text);
    const imported = getImportProfile(raw);
    if (imported.customQuestions.length) {
      imported.customQuestions = validateQuestionPack(imported.customQuestions, catalog.domains);
      const builtInIds = new Set(catalog.questions.map((question) => question.id));
      const collision = imported.customQuestions.find((question) => builtInIds.has(question.id));
      if (collision) throw new Error(`Backup question ID conflicts with the starter bank: ${collision.id}`);
    }
    const message = `Replace this browser's profile with ${imported.stats.sessions} session(s), ${imported.flashcards.length} review card(s), and ${imported.customQuestions.length} imported question(s)? This cannot be undone unless you exported a backup first.`;
    if (!window.confirm(message)) return;
    profile = imported;
    save();
    reviewQueue = [];
    lastResult = null;
    aiHistory = [];
    currentPage = "home";
    render();
    toast("Profile restored. Your AI key was not imported.", "success");
  }).catch((error) => toast(`Could not import this backup: ${error.message}`, "error"));
}

function importQuestionFile(file) {
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) {
    toast("Question packs must be 10 MB or smaller.", "error");
    return;
  }
  file.text().then((text) => {
    const parsed = JSON.parse(text);
    const questions = validateQuestionPack(parsed, catalog.domains);
    const known = new Set([...catalog.questions, ...profile.customQuestions].map((question) => question.id));
    const collision = questions.find((question) => known.has(question.id));
    if (collision) throw new Error(`Question ID already exists in your library: ${collision.id}`);
    profile.customQuestions.push(...questions);
    save();
    render();
    toast(`Imported ${questions.length} question${questions.length === 1 ? "" : "s"}. They are stored on this device.`, "success");
  }).catch((error) => toast(`Question pack not imported: ${error.message}`, "error"));
}

function resetProfile() {
  const confirmed = window.confirm("Delete your saved scores, imported questions, bookmarks, flashcards and local study plan from this browser? This cannot be undone without a backup.");
  if (!confirmed) return;
  profile = defaultProfile();
  try { localStorage.removeItem(AI_KEY_STORAGE_KEY); sessionStorage.removeItem(AI_KEY_STORAGE_KEY); } catch { /* Storage may be unavailable in strict private browsing. */ }
  aiKey = "";
  rememberAIKey = false;
  aiHistory = [];
  lastResult = null;
  reviewQueue = [];
  save();
  currentPage = "home";
  render();
  toast("Local progress and saved AI key cleared.", "success");
}

function runTask(task, domain) {
  if (task === "review") {
    startReviewQueue();
    return;
  }
  currentPage = "practice";
  render();
  if (task === "focus") startPractice({ domain: domain || "all", count: 10, mode: "practice" });
  else startPractice({ count: 10, mode: "practice" });
}

function retryMissedTopics() {
  if (!lastResult) return;
  const domains = [...new Set(lastResult.result.reviews.filter((item) => !item.correct).map((item) => item.question.domain))];
  if (domains.length === 1) startPractice({ domain: domains[0], count: 10, mode: "practice" });
  else startPractice({ count: 10, mode: "practice" });
}

function saveBackup() {
  const envelope = { app: "Kerala PSC Coach", backupVersion: 1, exportedAt: new Date().toISOString(), profile: exportableProfile(profile) };
  downloadFile(`kerala-psc-coach-backup-${localDateKey()}.json`, JSON.stringify(envelope, null, 2), "application/json");
  toast("Backup downloaded. API keys and AI conversations are excluded.", "success");
}

function saveFlashcardsCsv() {
  downloadFile("kerala-psc-flashcards.csv", flashcardCsv(), "text/csv;charset=utf-8");
  toast("Flashcards exported as CSV.", "success");
}

function handleClick(event) {
  const action = event.target.closest("[data-action]");
  if (!action) return;
  const kind = action.dataset.action;
  if (kind !== "navigate" && action.tagName === "A") event.preventDefault();
  switch (kind) {
    case "navigate": setPage(action.dataset.page); break;
    case "toggle-theme":
      profile.settings.theme = themeName() === "dark" ? "light" : "dark";
      save(); render(); break;
    case "open-more": document.querySelector("#more-dialog")?.showModal(); break;
    case "close-more": document.querySelector("#more-dialog")?.close(); break;
    case "install-app": showInstallHelp(); break;
    case "start-practice": startPractice(); break;
    case "answer": chooseAnswer(action.dataset.letter); break;
    case "previous-question": if (quiz) selectQuestion(quiz.current - 1); break;
    case "next-question": if (quiz) selectQuestion(quiz.current + 1); break;
    case "go-question": selectQuestion(Number(action.dataset.index)); break;
    case "toggle-flag": if (quiz) { const id = activeQuestion().id; quiz.flags.has(id) ? quiz.flags.delete(id) : quiz.flags.add(id); render(); } break;
    case "hint": if (quiz) { const id = activeQuestion().id; quiz.hints[id] = (quiz.hints[id] || 0) + 1; render(); } break;
    case "toggle-bookmark": toggleBookmark(action.dataset.qid); break;
    case "finish-quiz": finishQuiz(false); break;
    case "exit-quiz": setPage("practice"); break;
    case "run-task": runTask(action.dataset.task, action.dataset.domain); break;
    case "reveal-card": reviewRevealed = true; render(); break;
    case "rate-card": rateCurrentCard(action.dataset.quality); break;
    case "skip-card": reviewQueue.shift(); reviewRevealed = false; render(); break;
    case "ask-about-question": askAboutCurrentQuestion(); break;
    case "ask-about-review": askAboutReview(Number(action.dataset.reviewIndex)); break;
    case "return-to-quiz": currentPage = "quiz"; render(); break;
    case "ai-suggestion": aiPrefill = action.dataset.prompt || ""; render(); document.querySelector("#ai-prompt")?.focus(); break;
    case "clear-ai-chat": aiHistory = []; aiUsageLabel = ""; render(); break;
    case "new-math-drill": startMathDrill(); break;
    case "import-pack": document.querySelector("#question-pack-file")?.click(); break;
    case "download-template": createQuestionPackTemplate(); break;
    case "practice-bookmarks": startPractice({ bookmarksOnly: true, count: 20, mode: "practice" }); break;
    case "export-backup": saveBackup(); break;
    case "import-backup": document.querySelector("#backup-file")?.click(); break;
    case "export-csv": saveFlashcardsCsv(); break;
    case "reset-profile": resetProfile(); break;
    case "clear-ai-key":
      aiKey = ""; rememberAIKey = false;
      try { localStorage.removeItem(AI_KEY_STORAGE_KEY); sessionStorage.removeItem(AI_KEY_STORAGE_KEY); } catch { /* Storage may be unavailable in strict private browsing. */ }
      render(); toast("AI key removed from this tab and browser storage.", "success"); break;
    case "retry-missed": retryMissedTopics(); break;
    default: break;
  }
}

function showInstallHelp() {
  if (deferredInstallPrompt) {
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.finally(() => { deferredInstallPrompt = null; });
    return;
  }
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const browser = /android/i.test(navigator.userAgent)
    ? "On Android, use your browser menu and choose Install app or Add to Home screen."
    : ios
      ? "On iPhone or iPad, open this secure site in Safari, tap Share, then choose Add to Home Screen."
      : "In a supported desktop browser, use its Install app, Create shortcut or Add to dock menu. Firefox can keep this app pinned in a tab.";
  window.alert(`${browser}\n\nThe app needs to be served over HTTPS (or localhost for development) to install and cache for offline use.`);
}

function handleChange(event) {
  const target = event.target;
  if (target.id === "global-track" || target.id === "home-track" || target.id === "setting-track") {
    profile.settings.track = target.value;
    save(); render(); return;
  }
  if (target.id === "syllabus-track") {
    profile.settings.track = target.value;
    save(); render(); return;
  }
  if (target.id === "practice-track") {
    profile.settings.track = target.value;
    save(); render(); return;
  }
  if (target.id === "daily-goal") { profile.settings.dailyGoalMinutes = Number(target.value); save(); render(); return; }
  if (target.id === "theme-setting") { profile.settings.theme = target.value; save(); render(); return; }
  if (target.id === "setting-language" || target.id === "ai-language") { profile.settings.teachingLanguage = target.value; save(); if (target.id === "ai-language") render(); else render(); return; }
  if (target.id === "setting-style" || target.id === "ai-style") { profile.settings.teachingStyle = target.value; save(); render(); return; }
  if (target.id === "negative-setting") { profile.settings.negativeMarking = target.checked; save(); return; }
  if (target.id === "ai-provider") {
    const previous = profile.settings.aiProvider;
    profile.settings.aiProvider = target.value;
    if (profile.settings.aiModel === AI_PROVIDERS[previous]?.defaultModel) profile.settings.aiModel = AI_PROVIDERS[target.value].defaultModel;
    save(); render(); return;
  }
  if (target.id === "include-learning-profile") { profile.settings.includeLearningProfile = target.checked; save(); render(); return; }
  if (target.id === "remember-ai-key") {
    rememberAIKey = target.checked;
    try {
      if (rememberAIKey && aiKey) localStorage.setItem(AI_KEY_STORAGE_KEY, aiKey);
      else localStorage.removeItem(AI_KEY_STORAGE_KEY);
    } catch {
      rememberAIKey = false;
      toast("This browser cannot persist the key. It will remain only in this tab.", "error");
    }
    render(); return;
  }
  if (target.id === "calculator-kind") { currentMathKind = target.value; currentMathResult = null; render(); return; }
  if (target.id === "calc-target") { currentMathTarget = target.value; currentMathResult = null; render(); return; }
  if (target.dataset.taskToggle) {
    setDailyTask(profile, target.dataset.taskToggle, target.checked);
    save(); render(); return;
  }
  if (target.id === "question-pack-file") { importQuestionFile(target.files?.[0]); target.value = ""; return; }
  if (target.id === "backup-file") { importBackupFile(target.files?.[0]); target.value = ""; }
}

function handleInput(event) {
  const target = event.target;
  if (target.id === "ai-key") updateAIKey(target.value);
  if (target.id === "ai-model") {
    profile.settings.aiModel = target.value.trim().slice(0, 120);
    save();
  }
}

function handleSubmit(event) {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  if (form.id === "practice-form") { event.preventDefault(); startPractice({ formData: new FormData(form) }); return; }
  if (form.id === "ai-form") { event.preventDefault(); sendAIRequest(form); return; }
  if (form.id === "math-calculator-form") {
    event.preventDefault();
    try {
      const data = Object.fromEntries(new FormData(form).entries());
      const kind = data.kind;
      delete data.kind;
      currentMathKind = kind;
      currentMathTarget = data.target || currentMathTarget;
      currentMathResult = solveMath(kind, data);
      render();
    } catch (error) { toast(error.message, "error"); }
    return;
  }
  if (form.id === "math-drill-form") { event.preventDefault(); checkMathDrill(form); }
}

function addGlobalListeners() {
  appRoot.addEventListener("click", handleClick);
  appRoot.addEventListener("change", handleChange);
  appRoot.addEventListener("input", handleInput);
  appRoot.addEventListener("submit", handleSubmit);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && currentPage === "quiz" && quiz) return;
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && currentPage === "ai" && !aiBusy) {
      event.preventDefault();
      document.querySelector("#ai-form")?.requestSubmit();
    }
  });
  globalThis.addEventListener?.("online", () => {
    const pill = document.querySelector("#network-pill");
    const label = document.querySelector("#network-label");
    pill?.classList.remove("offline"); if (label) label.textContent = aiKey ? "AI key ready" : "Online · local profile";
  });
  globalThis.addEventListener?.("offline", () => {
    const pill = document.querySelector("#network-pill");
    const label = document.querySelector("#network-label");
    pill?.classList.add("offline"); if (label) label.textContent = "Offline mode";
  });
  globalThis.addEventListener?.("beforeinstallprompt", (event) => {
    event.preventDefault(); deferredInstallPrompt = event;
    const button = document.querySelector(".install-button"); if (button) button.textContent = "Install app";
  });
  globalThis.addEventListener?.("appinstalled", () => {
    deferredInstallPrompt = null; toast("Kerala PSC Coach added to your device.", "success");
  });
  globalThis.matchMedia?.("(prefers-color-scheme: light)")?.addEventListener?.("change", () => {
    if (profile.settings.theme === "system") render();
  });
}

async function initialize() {
  try {
    const rememberedKey = localStorage.getItem(AI_KEY_STORAGE_KEY) || "";
    rememberAIKey = Boolean(rememberedKey);
    aiKey = rememberedKey;
  } catch {
    rememberAIKey = false;
    aiKey = "";
  }
  try {
    const response = await fetch("./data/starter-bank.json", { cache: "default" });
    if (!response.ok) throw new Error(`Could not load offline question bank (HTTP ${response.status}).`);
    catalog = await response.json();
    if (catalog.schemaVersion !== 1 || !Array.isArray(catalog.questions)) throw new Error("The bundled question bank has an unsupported format.");
    profile = normalizeProfile(profile);
    const shortcut = new URL(location.href).searchParams.get("screen");
    if (["practice", "review"].includes(shortcut)) currentPage = shortcut;
    if (shortcut === "review") reviewQueue = dueFlashcards(profile).map((card) => card.id);
    addGlobalListeners();
    render();
    if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
      navigator.serviceWorker.register("./service-worker.js", { scope: "./" }).catch(() => toast("Offline caching could not start. The app still works while this page is open.", "error"));
    }
    if (navigator.storage?.persist) navigator.storage.persist().catch(() => {});
  } catch (error) {
    appRoot.innerHTML = `<main class="page card" style="max-width:680px;margin:10vh auto"><div class="eyebrow">Startup problem</div><h1>Could not open the study bank</h1><p class="muted">${esc(error.message)}</p><p class="small-text muted">Run this app from its HTTPS site or start the local server with <code>python3 run_web.py</code>. The question bank is a local file that must be served with the app.</p></main>`;
  }
}

initialize();
