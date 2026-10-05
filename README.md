# Kerala PSC Coach

An offline-first Kerala PSC study coach for **LDC / 10th Level**, **Plus Two Level**, **Degree Level** and related posts. It includes the existing Windows desktop edition and a responsive, installable **Progressive Web App (PWA)** for modern Windows, macOS, Linux, Android and iPhone browsers. Syllabus-aware practice, timed mocks, local progress, spaced-review flashcards and the Math Lab work without an account or AI key.

> This is an independent educational tool, not a Kerala PSC or Government of Kerala app. Its starter questions are original practice examples, not official questions or a past-paper archive. Practice can help you find gaps; it cannot guarantee a pass, rank or selection. Always follow the latest notification for your post.

## What is upgraded

- **Cross-platform PWA:** install from a secure website to a Windows, macOS, Linux, Android or iPhone home screen. After the first load, the app shell and question bank cache for offline practice; profile data stays in that browser.
- **Classic Windows desktop edition:** the existing Tkinter app remains available as a portable EXE and in-place-upgrade installer. The same syllabus blueprints and starter questions feed both editions.
- **Works offline; AI is optional.** Practice, adaptive selection, math tools and flashcards need no API key, account, sign-in or cloud service.
- **Three exam tracks:** LDC / 10th Level, Plus Two Level, and Degree Level, with their mark-weighted practice blueprints.
- **Subject and topic practice** across Kerala and Indian history, renaissance, geography, civics, economics, the Constitution, arts and literature, sports, biology, physics, chemistry, science and technology, computer basics, English, Malayalam, and aptitude.
- **Fresh aptitude practice:** arithmetic and reasoning items are generated locally so different sessions have new numbers and no question repeats inside a session.
- **Math Lab:** twelve step-by-step calculators (percentages, percentage change, averages, ratios, simple interest, profit/loss, speed-distance-time, time/work, discounts, HCF/LCM, rectangle mensuration and fractions) plus fresh mental-maths drills with worked solutions and memorable shortcuts.
- **Dark-first interface:** the app opens in dark mode, with themed forms, tables, charts, scrolling and dropdowns. Switch to light mode from the top bar or Library & Settings; the choice is remembered on this device.
- **Learn-as-you-go mode** reveals the answer and explanation after each response. **Timed mock mode** hides feedback until submission, includes a question map, timer, review flags and optional one-third negative marking.
- **Automatic coaching loop:** subject accuracy, repeated errors, hints used, response pace and due cards guide the next adaptive practice mix and daily study checklist. Wrong and skipped answers become flashcards.
- **Optional Gemini / OpenRouter tutor:** adapt explanations to the learner's selected style and language; optionally share a short performance summary so the tutor can target recurring topics. Each provider request requires explicit send consent.
- **Bring your own AI key (BYOK):** no shared key is embedded. Keys stay in memory unless the learner explicitly opts to remember one in that browser; keys, chat and performance history are excluded from backups by default. Provider privacy and usage fees still apply.
- **Spaced review** schedules cards from recall ratings: Again, Hard, Good or Easy.
- **Transparent progress:** accuracy by subject, score trends, streaks and session history.
- **Your own question packs:** import dated current-affairs, Tamil, Kannada or subject questions from JSON; export a local profile backup and flashcards as CSV.
- **Legacy profile migration:** the previous `~/.kerala_psc_v11.json` scores and flashcards are imported once where available; old API keys are deliberately not carried over.
- **One-click Windows packaging** locally with `build_exe.bat`, or automatically in GitHub Actions after code changes.

## Exam tracks and official syllabus references

The weights below are the app's practice blueprints based on the linked Kerala PSC syllabi. They are not a substitute for the notification of a particular post or exam cycle.

| Track | Blueprint used in the app | Official reference |
|---|---|---|
| **10th Level / LDC** | 60 marks: General Knowledge, Current Affairs & Renaissance in Kerala; 20: General Science; 20: Simple Arithmetic & Mental Ability | [10th Level preliminary syllabus (Kerala PSC)](https://www.keralapsc.gov.in/sites/default/files/inline-files/10th_level.pdf) |
| **Plus Two Level** | History 5, Geography 5, Civics 5, Economics 5, Constitution 5, Biology 5, Physics & Chemistry 5, Computer Science 5, Arts/Sports/Literature 5, Current Affairs 5, Arithmetic/Mental Ability 20, English 20, Regional Language 10 | [Plus Two Level common preliminary syllabus (Kerala PSC)](https://www.keralapsc.gov.in/sites/default/files/inline-files/syllabus_plus_two_level_preliminary_exam_2022.pdf) |
| **Degree Level** | History 10, Geography 5, Economics 5, Civics 5, Constitution 5, Arts/Literature/Culture/Sports 10, Computer 5, Science & Technology 5, Arithmetic/Mental Ability/Reasoning 20, English 20, Regional Language 10 | [Revised Degree Level common preliminary syllabus and marks (Kerala PSC, 2025)](https://www.keralapsc.gov.in/sites/default/files/2025-01/degree_level_preliminary_revised_latest_.pdf) |

Some common preliminary syllabi include current affairs within a broader General Knowledge or subject section; the UI preserves that distinction. **No dated current-affairs claims are bundled.** The app flags this and lets you add your own questions with source and publication date. Current-affairs and post-specific coverage must be refreshed from official sources.

## Cross-platform Progressive Web App

The PWA is the recommended edition for **Linux, macOS, Windows, Android and iPhone/iPad**. It uses the browser rather than a platform-specific native installer, has large touch targets and phone-safe layouts, and caches its static app shell and question bank after the first visit. Practice, progress, flashcards and Math Lab work offline; AI requests need an internet connection.

- When GitHub Pages is enabled for this repository, open **<https://afzalashraf.github.io/PSC-Coaching-App/>** over HTTPS. On Android or desktop Chromium, use **Install app** or the browser's install menu. On iPhone/iPad, open the site in Safari, tap **Share → Add to Home Screen**.
- For local development, run `python3 run_web.py` on macOS/Linux or `py -3 run_web.py` on Windows, then open **<http://127.0.0.1:8000/>**. `run-web.sh` and `run-web.bat` are included for convenience.
- Installable offline caching requires HTTPS (or `localhost` during development). A phone visiting another computer's plain HTTP LAN address cannot install the PWA; use the public HTTPS address for mobile installation.
- Browser storage is separate on each device and is not silently synced. Use **Settings → Export profile backup** on one device and **Import/restore backup** on another. The browser app can import existing desktop JSON profile backups.

The PWA is a browser-installable app, **not a native Google Play or Apple App Store package**. The classic Tkinter desktop edition is still available separately.

## Quick start

### Run the classic Tkinter desktop edition

1. Install Python 3.10 or newer (the Windows installer should include Tcl/Tk).
2. Download or clone this repository.
3. Double-click `PSCapp.pyw`, or run:

   ```bash
   python PSCapp.pyw
   ```

No `pip install` is needed to use the app. On a minimal Linux installation, install that distribution's Tkinter package (often named `python3-tk`).

### First session

1. Select **LDC / 10th Level**, **Plus Two Level**, or **Degree Level**.
2. Choose a subject and topic, or leave them on **All** for a mixed practice session.
3. Select **Learn as you go** or **Timed mock**, then pick the question count.
4. Review the explanations. Your missed questions are saved as due flashcards.
5. Check **Overview** for today's plan and **My Progress** for subject accuracy and trends.
6. Open **Math Lab** for guided arithmetic, formula-based calculators, worked solutions and short memory cues.

## Current affairs and question packs

The app intentionally does not claim that a static list of headlines is current. Open official sources from **Practice & Mocks** or **Library & Settings**, prepare dated questions, and import them as a `.json` pack. This also allows a teacher or study group to share original questions in Malayalam, Tamil or Kannada.

A template is provided at [`examples/question-pack-template.json`](examples/question-pack-template.json). Replace every example placeholder before importing. Supported domains are:

```text
history, geography, economics, civics, constitution, arts,
biology, physics_chemistry, science_technology, computer,
current_affairs, quantitative, english, malayalam, tamil, kannada
```

Question format:

```json
{
  "version": 1,
  "questions": [
    {
      "id": "kerala-history-001",
      "domain": "history",
      "topic": "Kerala Renaissance",
      "question": "Write an original multiple-choice question here.",
      "options": {
        "A": "Option one",
        "B": "Option two",
        "C": "Option three",
        "D": "Option four"
      },
      "answer": "B",
      "explanation": "Explain the answer in clear language.",
      "mnemonic": "Optional memory hook or acronym.",
      "source_hint": "Source URL or book; publication date for time-sensitive facts"
    }
  ]
}
```

Each question needs four distinct choices, a unique ID, a supported domain and one correct answer. Packs are validated locally; importing JSON does not execute code. Keep current-affairs source/date details with the item and check them again before the exam.

## Data and privacy

The classic desktop profile is saved to the platform's user-data directory:

- **Windows:** `%APPDATA%\KeralaPSC Coach\profile.json`
- **macOS:** `~/Library/Application Support/KeralaPSC Coach/profile.json`
- **Linux:** `$XDG_DATA_HOME/kerala-psc-coach/profile.json` (defaults to `~/.local/share/kerala-psc-coach/profile.json`)

The PWA keeps its profile in that browser's local site storage. It does not silently sync or send practice history to the app repository. Use **Settings → Export profile backup** to move a profile between devices, and **Export flashcards (CSV)** for spreadsheet or Anki-style workflows. Backups exclude API keys and AI chat transcripts.

**Optional AI privacy:** if you configure Gemini or OpenRouter, each tutor prompt you approve, along with a few recent messages from that in-tab chat, is sent directly from your browser to that provider using your own key. The default request includes your question and teaching preferences; a minimal, aggregated study summary (weak subjects, repeated difficult topics, response pace and hints) is included only if you opt in, and the send checkbox is still required for every request. The app does not receive the provider response through its server. Provider data retention and charges are subject to the provider's terms. The key is memory-only by default; if you explicitly choose “Remember this key”, it is stored in browser local storage, which is not a secure vault and can be accessed by someone with access to your browser profile. Never use a shared key or put a key in a backup. If you reset progress, that action is permanent unless you have a backup.

### Configure the optional AI tutor

1. Open **Settings → Optional AI provider** and select **Google Gemini** or **OpenRouter**.
2. Create a personal API key with [Google AI Studio](https://aistudio.google.com/app/apikey) or [OpenRouter](https://openrouter.ai/settings/keys). The default model IDs are editable and may change; check the provider's current model list, pricing and data terms. OpenRouter's default `openrouter/free` router can have availability or rate limits.
3. Paste the key in this browser. It is held in tab memory by default. Only use **Remember this key on this device** if this is your own protected browser profile; browser storage is not a secret vault.
4. In **AI Coach**, choose a teaching language and style. If you want the coach to see a small aggregate of your weaker subjects and repeated difficult topics, opt in to **Include a minimal study summary**. Read the per-request notice and tick the send-consent box before every call.

The PWA sends requests directly to the chosen provider over HTTPS; there is no shared application key or server-side proxy. This avoids exposing a repository-wide secret or charging all learners to one account, but each learner is responsible for their own key and usage. Do not paste sensitive personal information. For a centrally managed consumer service, deploy a properly authenticated, rate-limited backend with server-held credentials instead of putting an app-wide API key in browser code.

## Build a Windows executable

### One click on Windows

Install Python 3.10+ from python.org, then double-click:

```text
build_exe.bat
```

The script installs the build-only PyInstaller dependency, runs the test suite, and writes:

```text
dist\KeralaPSCCoach.exe
```

The EXE stores the learner's profile in the user's app-data directory, not beside the executable.

### Automatic build, rolling release and in-place updates

The workflow is at **`.github/workflows/build-exe.yml`** and appears in GitHub Actions as **Build and release Windows EXE**. It runs tests, builds both a portable EXE and an installer on a Windows runner, and then updates a rolling GitHub Release tagged `latest` when code is pushed to `main` or this Arena branch. Pull requests build and test but do not publish a release.

1. Push the updated code to `main` or `arena/01a106e9-psc-coaching-app`.
2. Open **GitHub → Actions → Build and release Windows EXE** to watch the run. To build on demand, choose **Run workflow** and select one of those branches.
3. For the public download, open **GitHub → Releases → Latest**. It contains:
   - `KeralaPSCCoach-Setup.exe` — recommended for installing and updating.
   - `KeralaPSCCoach.exe` — portable executable.
4. Alternatively, download **KeralaPSC-Coach-Windows** from the run's **Artifacts** section. Artifacts are retained for 30 days.

**Updating an existing install:** run the newest `KeralaPSCCoach-Setup.exe` over the current install. It uses the same stable Inno Setup application ID and per-user install location, so users do not need to manually uninstall first. Scores, flashcards and imported questions live separately in the user's profile and are preserved. The app's **Library & Settings → Get latest installer** button opens the rolling release page. This release automation requires the GitHub repository to be public for anyone to download it; it uses the built-in GitHub token and no repository secrets.

The local `build_exe.bat` still creates the portable `dist\\KeralaPSCCoach.exe`; the GitHub Windows workflow additionally produces the setup installer and publishes both assets.

The same project is tested in a separate Python test workflow. Local commands:

```bash
python -m compileall -q PSCapp.pyw psc_coach tests
python -m unittest discover -s tests -v
```

## Learning design

The app uses retrieval practice, a steady daily plan and scheduled review rather than relying only on rereading. Missed items return as flashcards; the learner rates recall and the next review interval changes accordingly. Short memory hooks are shown alongside selected explanations and carry into review cards; custom question packs may include their own mnemonic. Math Lab encourages an estimate first, a clear formula, step-by-step substitution and then a quick self-test. Adaptive practice prioritises weaker subjects, while timed mocks preserve the selected syllabus blueprint as closely as the available question bank allows. Any missing or lighter section is called out instead of silently represented as official coverage.

## Development notes

- **Classic desktop runtime:** Python 3.10+ and Tkinter; Windows packaging uses PyInstaller (`requirements-build.txt`).
- **PWA runtime:** static HTML/CSS/JavaScript modules, a service worker and local browser storage; no framework, CDN or third-party runtime package is required.
- **PWA local server:** `python3 run_web.py` (or `py -3 run_web.py` on Windows). The app binds to port 8000 by default; set `PORT` to change it.
- **Source of truth:** `psc_coach/catalog.py` and `psc_coach/data/bank.py`; run `python tools/export_web_data.py` to regenerate `web/data/starter-bank.json`.
- **Python tests:** `python -m unittest discover -s tests -v`.
- **PWA tests:** Node.js 22+; run `npm test --prefix web`. No `npm install` is needed.
- **Workflows:** `.github/workflows/build-exe.yml` tests and publishes Windows builds; `.github/workflows/pwa.yml` checks the PWA and deploys its static files to GitHub Pages when Pages is enabled.
- **Desktop storage:** atomic local JSON profile. **PWA storage:** per-browser local profile with JSON backup/import.
- **Classic desktop entrypoint:** `PSCapp.pyw`.

Contributions that expand the original question bank should include a clear explanation and a checkable source hint for factual claims. Do not copy copyrighted app content or describe unofficial questions as official previous-year questions.
