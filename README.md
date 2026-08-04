# Kerala PSC Mock Exam Simulator

**AI-powered adaptive exam engine with spaced repetition and mnemonic teaching.**

One file. Zero setup. Just run `python PSCapp.py` and start learning.

---

## What It Does

| Feature | Description |
|---|---|
| **Full Mock Exams** | Take 5 / 10 / 15 / 25 / 50 question exams across Polity, Math, Science, GK |
| **Kerala PSC Focused** | Questions cover Constitution, Kerala history, geography, renaissance, culture, Malayalam literature, current affairs |
| **AI-Graded Analysis** | Every question reviewed with detailed explanation after submission |
| **8 Mnemonic Techniques** | Acronyms, acrostics, chunking, rhymes, visual, loci, story, Malayalam wordplay |
| **Feynman Method** | Complex concepts explained as if to a 10-year-old |
| **Spaced Repetition** | Wrong answers become flashcards with Leitner box scheduling |
| **Adaptive Difficulty** | AI adjusts complexity based on your accuracy trend |
| **Persistent Profile** | API key, scores, weak areas, flashcards saved in JSON — never re-enter anything |
| **Parallel Generation** | Large exams generated in parallel batches for 3x speed |
| **Knowledge Base** | Upload PDFs, paste notes, extract YouTube transcripts as study material |

---

## Screenshots

```
Setup Page        Config Page         Exam Page          Analysis Page       Flashcard Review
+-----------+     +-----------+      +-----------+      +-----------+      +-----------+
| Provider  |     | Profile   |      | Q 3/10    |      | 72%       |      | Card 2/8  |
| API Key   |     | Stats     |      | [Question]|      | Grade B+  |      | [Question]|
| Continue  |     | Flashcard |      | A B C D   |      | Explain   |      | Show Ans  |
|           |     | Review    |      | Nav Grid  |      | Mnemonic  |      | Forgot    |
|           |     | Begin Exam|      | Submit    |      | Feynman   |      | Good Easy |
+-----------+     +-----------+      +-----------+      +-----------+      +-----------+
```

---

## Quick Start

```bash
# Just run it. Everything installs automatically.
python PSCapp.py
```

### Requirements

- Python 3.10+
- Internet connection (for AI API calls)
- Free API key from one of:

| Provider | Get Key | Cost |
|---|---|---|
| **Google Gemini** (recommended) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Free |
| **OpenRouter Nemotron** | [openrouter.ai/keys](https://openrouter.ai/keys) | Free |
| **OpenRouter Llama 4** | [openrouter.ai/keys](https://openrouter.ai/keys) | Free |

### Auto-Installed Packages

The app automatically installs these on first run:

```
customtkinter    Modern UI framework
google-genai     Gemini API (new SDK)
openai           OpenRouter API
PyPDF2           PDF text extraction
Pillow           Logo image handling
youtube-transcript-api  YouTube transcript extraction
```

---

## How It Works

### Exam Flow

```
1. Setup          Enter API key (saved permanently)
      |
2. Config         Choose questions, difficulty, upload study material
      |           Review flashcards from previous mistakes
      |
3. Exam           Answer all questions with timer and navigator
      |           Skip, revisit, change answers freely
      |
4. Submit         Confirm and submit all answers
      |
5. Score Reveal   Animated percentage counter with grade
      |
6. Full Analysis  For EVERY question:
      |             - Why correct answer is right
      |             - Why wrong options are wrong
      |             - Mnemonic trick (8 techniques)
      |             - Feynman explanation (simple language)
      |             - Connected knowledge web
      |             - Related topics to study
      |             - Exam strategy tip
      |             - Flashcard auto-created for wrong answers
      |
7. Back to Config Take another exam or review flashcards
```

### Adaptive Learning Engine

```
Your Exam History
    |
    v
Profile JSON tracks:
  - Accuracy per subject
  - Weak areas identified
  - Common mistake subjects
  - Improvement trend (last 20 exams)
    |
    v
AI receives your profile and:
  - Gives MORE questions on weak topics
  - Gives HARDER questions on strong topics
  - Adjusts difficulty automatically
  - Targets your specific mistake patterns
```

### Spaced Repetition (Leitner System)

```
Wrong answer on exam
    |
    v
Flashcard created automatically
    |
    v
Box 1 (review daily)
    |  Got it right
    v
Box 2 (review every 3 days)
    |  Got it right
    v
Box 3 (review weekly)
    |  Got it right
    v
Box 4 (review every 16 days)
    |  Got it right
    v
Box 5 (review every 45 days)

Got it wrong at any stage? Back to Box 1.
```

### Mnemonic Techniques Used

| Technique | Example |
|---|---|
| **Acronym** | CCC FRENS = Coal, Crude, Cement, Fertilizers, Refinery, Electricity, Natural Gas, Steel |
| **Acrostic** | My Very Educated Mother Just Served Us Noodles = planet order |
| **Chunking** | Article 3-6-8 = 3 readings, 6 months, 8th schedule |
| **Number Rhyme** | Teen Sau FIFTEEN = Article 315 |
| **Visual** | Imagine Velu Thampi riding a giant sword on Travancore palace |
| **Loci** | Kitchen = Kerala Rivers (water), Bedroom = Kerala Culture (rest) |
| **Story** | Sree Narayana Guru sat under a coconut tree teaching ONE caste... |
| **Malayalam Wordplay** | PERIyar = longest PERIod of flow = longest river |

---

## Kerala PSC Topics Covered

### Polity
- Indian Constitution articles, amendments, schedules
- Fundamental Rights, Duties, DPSPs
- Emergency provisions (352, 356, 360)
- Panchayati Raj, Kerala Panchayat Raj Act 1994
- Constitutional bodies (KPSC, CAG, Election Commission)
- Landmark Supreme Court cases

### Kerala GK
- **History**: Ay, Chera, Kulasekhara, Zamorins, Travancore, Marthanda Varma, Velu Thampi, Pazhassi Raja, Temple Entry 1936, Vaikom 1924, Guruvayoor 1931, Kerala formation 1956
- **Geography**: 14 districts, 44 rivers, Periyar, Anamudi, Vembanad, Kuttanad, Western Ghats
- **Renaissance**: Sree Narayana Guru, Ayyankali, Chattampi Swamikal, Kumaranasan, SNDP, NSS
- **Culture**: Kathakali, Mohiniyattam, Theyyam, Koodiyattam (UNESCO), Onam, Thrissur Pooram
- **Literature**: Ezhuthachan, Kavithrayam, ONV Kurup, MT Vasudevan Nair, Basheer

### Math / Mental Ability
- Number series, coding-decoding, blood relations
- Profit/loss, percentage, time-speed-distance
- LCM/HCF, area/volume, data interpretation

### General Science
- Physics, Chemistry, Biology fundamentals
- Vitamins and deficiency diseases
- ISRO missions, scientific instruments

---

## Profile Storage

Everything saved automatically to:

```
Windows:  C:\Users\YourName\.kerala_psc_v11.json
Mac:      /Users/YourName/.kerala_psc_v11.json
Linux:    /home/YourName/.kerala_psc_v11.json
```

### Profile Structure

```json
{
  "provider": "gemini",
  "api_key": "AIzaSy...",
  "exams": 12,
  "qs": 150,
  "correct": 98,
  "weak": ["Kerala History", "Constitutional Amendments"],
  "scores": {
    "Polity": {"t": 40, "c": 28},
    "Math": {"t": 35, "c": 30},
    "Science": {"t": 38, "c": 25},
    "GK": {"t": 37, "c": 15}
  },
  "lp": {
    "diff": 7,
    "best": "Math",
    "worst": "GK",
    "trend": [45, 52, 60, 68, 72, 75]
  },
  "flashcards": [
    {
      "front": "Longest river in Kerala?",
      "back": "Periyar (244km) -- PERIyar = longest PERIod",
      "mnemonic": "PERIyar flows for the longest PERIod",
      "feynman": "Think of it like the longest road in your city...",
      "box": 2,
      "interval": 3,
      "next_review": "2025-01-15"
    }
  ]
}
```

---

## Exam Categories Supported

| Category | Examples |
|---|---|
| **LGS** | Last Grade Servant |
| **LDC** | Lower Division Clerk |
| **UDC** | Upper Division Clerk |
| **Degree Level** | Preliminary exam |
| **KAS** | Kerala Administrative Service |
| **Police** | Constable, SI, Excise Inspector |
| **Secretariat** | Secretariat Assistant |
| **Teaching** | LP/UP/HS Assistant |

---

## Tech Stack

| Component | Technology |
|---|---|
| UI Framework | CustomTkinter (modern dark-mode widgets) |
| AI Backend | Google Gemini 2.5 Flash / OpenRouter (Nemotron, Llama) |
| Data Format | Structured JSON with enforced schema |
| Storage | Local JSON profile (no cloud, no account needed) |
| PDF Processing | PyPDF2 |
| YouTube | youtube-transcript-api |
| Image | Pillow (for logo rendering) |

---

## Architecture

```
PSCapp.py (single file)
|
+-- Auto-installer (installs all packages on first run)
|
+-- Profile system (JSON read/write with Leitner SRS tracking)
|
+-- LLM Service (Gemini / OpenRouter with retry + JSON cleaning)
|
+-- Adaptive prompt builder (uses profile data to customize AI output)
|
+-- UI Pages:
    +-- Setup (provider + API key)
    +-- Config (questions, difficulty, KB, flashcard review access)
    +-- Exam (question navigator, timer, options)
    +-- Loader (real progress percentage)
    +-- Score Reveal (animated counter)
    +-- Analysis (7-layer teaching per question)
    +-- Flashcard Review (Leitner box SRS)
```

---

## Contributing

This is a single-file application by design.
To contribute, fork and modify `PSCapp.py` directly.

Key areas for contribution:
- Additional mnemonic techniques
- More Kerala PSC topic coverage
- UI improvements
- Alternative AI provider support
- Flashcard export (Anki format)

---

## License

MIT License. Free to use, modify, and distribute.

---

## Version History

| Version | Changes |
|---|---|
| v11 | Flashcard review page, no emojis, Leitner SRS, clean UI |
| v10 | Logo integration, 8 mnemonic techniques, Feynman method, SRS |
| v9 | Custom titlebar, animated score reveal, real progress tracking |
| v8 | Persistent JSON profile, parallel generation, adaptive prompts |
| v7 | Full exam mode (answer all then review), knowledge base |
| v6 | CustomTkinter migration, modern UI |
| v5 | Kerala PSC focus, dark theme |
| v4 | Python 3.14 fixes, multi-provider support |

---

*Built for Kerala PSC aspirants who believe in learning smart, not just hard.*
