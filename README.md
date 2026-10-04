# Kerala PSC Coach

An offline-first desktop coach for Kerala PSC aspirants preparing for **LDC / 10th Level**, **Plus Two Level**, and **Degree Level** common preliminary exams. It combines syllabus-aware practice, timed mocks, clear explanations, a personalised daily plan, progress tracking and spaced-review flashcards.

> This is an independent educational tool, not a Kerala PSC or Government of Kerala app. Its starter questions are original practice examples, not official questions or a past-paper archive. Practice can help you find gaps; it cannot guarantee a pass, rank or selection. Always follow the latest notification for your post.

## What is upgraded

- **Works offline and needs no API key.** The app uses Python's standard library at runtime; there is no auto-installer, account, sign-in or cloud service.
- **Three exam tracks:** LDC / 10th Level, Plus Two Level, and Degree Level, with their mark-weighted practice blueprints.
- **Subject and topic practice** across Kerala and Indian history, renaissance, geography, civics, economics, the Constitution, arts and literature, sports, biology, physics, chemistry, science and technology, computer basics, English, Malayalam, and aptitude.
- **Fresh aptitude practice:** arithmetic and reasoning items are generated locally so different sessions have new numbers and no question repeats inside a session.
- **Learn-as-you-go mode** reveals the answer and explanation after each response. **Timed mock mode** hides feedback until submission, includes a question map, timer, review flags and optional one-third negative marking.
- **Automatic coaching loop:** weak subject scores feed an adaptive practice mix and a daily study checklist. Wrong and skipped answers become flashcards.
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

## Quick start

### Run with Python

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
      "source_hint": "Source URL or book; publication date for time-sensitive facts"
    }
  ]
}
```

Each question needs four distinct choices, a unique ID, a supported domain and one correct answer. Packs are validated locally; importing JSON does not execute code. Keep current-affairs source/date details with the item and check them again before the exam.

## Data and privacy

Scores, study streak, imported questions and flashcards are saved locally to:

- **Windows:** `%APPDATA%\KeralaPSC Coach\profile.json`
- **macOS:** `~/Library/Application Support/KeralaPSC Coach/profile.json`
- **Linux:** `$XDG_DATA_HOME/kerala-psc-coach/profile.json` (defaults to `~/.local/share/kerala-psc-coach/profile.json`)

Use **Library & Settings → Export progress backup** to make a portable JSON backup. Use **Export flashcards (CSV)** for spreadsheet or Anki-style workflows. Your data is not sent to a server. If you reset progress, the action is permanent unless you have a backup.

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

The app uses retrieval practice, a steady daily plan and scheduled review rather than relying only on rereading. Missed items return as flashcards; the learner rates recall and the next review interval changes accordingly. Adaptive practice prioritises weaker subjects, while timed mocks preserve the selected syllabus blueprint as closely as the available question bank allows. Any missing or lighter section is called out instead of silently represented as official coverage.

## Development notes

- **Runtime:** Python 3.10+ and Tkinter only.
- **Build-only dependency:** PyInstaller (`requirements-build.txt`).
- **Tests:** standard-library `unittest`; no network or third-party test package required.
- **Storage:** atomic local JSON profile.
- **Entrypoint:** `PSCapp.pyw`.

Contributions that expand the original question bank should include a clear explanation and a checkable source hint for factual claims. Do not copy copyrighted app content or describe unofficial questions as official previous-year questions.
