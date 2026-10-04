"""Question-bank loading, validation and offline aptitude question generation."""

from __future__ import annotations

import json
import random
import re
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from .catalog import DOMAIN_LABELS
from .data.bank import SEED_QUESTIONS

MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_IMPORTED_QUESTIONS = 5_000
LETTERS = "ABCD"


class QuestionPackError(ValueError):
    """Raised when an imported practice-question pack is invalid."""


def normalize_question(raw: dict[str, Any], *, fallback_id: str | None = None) -> dict[str, Any]:
    """Validate one question and return the app's canonical question shape.

    Accepted answer forms are A-D, a zero-based option index, or the exact
    option text. Options may be a four-item list or an A-D mapping.
    """
    if not isinstance(raw, dict):
        raise QuestionPackError("Each question must be a JSON object.")

    question_text = str(raw.get("question", raw.get("prompt", raw.get("question_text", "")))).strip()
    domain = str(raw.get("domain", "")).strip().lower()
    topic = str(raw.get("topic", "General practice")).strip() or "General practice"
    if not question_text:
        raise QuestionPackError("A question is missing its question text.")
    if len(question_text) > 2_000:
        raise QuestionPackError("Question text must be 2,000 characters or fewer.")
    if domain not in DOMAIN_LABELS:
        valid = ", ".join(DOMAIN_LABELS)
        raise QuestionPackError(f"Unknown domain '{domain}'. Use one of: {valid}.")

    raw_options = raw.get("options", raw.get("choices"))
    if isinstance(raw_options, dict):
        try:
            options = [str(raw_options[key]).strip() for key in LETTERS]
        except KeyError as exc:
            raise QuestionPackError("Options must contain A, B, C and D.") from exc
    elif isinstance(raw_options, list):
        options = [str(option).strip() for option in raw_options]
    else:
        raise QuestionPackError("Options must be a four-item list or an A-D object.")

    if len(options) != 4 or any(not option for option in options):
        raise QuestionPackError("Every question must have exactly four non-empty options.")
    if len({option.casefold() for option in options}) != 4:
        raise QuestionPackError("The four answer options must be distinct.")

    raw_answer = raw.get("answer", raw.get("correct_option", raw.get("correct_answer")))
    if raw_answer is None:
        raise QuestionPackError("A question is missing its correct answer.")
    answer_text = str(raw_answer).strip()
    if answer_text.upper() in LETTERS:
        answer_index = LETTERS.index(answer_text.upper())
    elif answer_text.isdigit() and 0 <= int(answer_text) < 4:
        answer_index = int(answer_text)
    else:
        try:
            answer_index = options.index(answer_text)
        except ValueError as exc:
            raise QuestionPackError("Answer must be A-D, an option index, or exact option text.") from exc

    qid = str(raw.get("id", fallback_id or "")).strip()
    if not qid:
        raise QuestionPackError("A question is missing its id.")
    if len(qid) > 100:
        raise QuestionPackError("Question id must be 100 characters or fewer.")
    explanation = str(raw.get("explanation", raw.get("feedback", ""))).strip()
    if len(explanation) > 4_000:
        raise QuestionPackError("Explanation must be 4,000 characters or fewer.")
    source_hint = str(raw.get("source_hint", raw.get("source", ""))).strip()
    if domain == "current_affairs" and not source_hint:
        raise QuestionPackError("Current-affairs questions need a source_hint with a publisher and publication date.")
    difficulty_raw = raw.get("difficulty", 4)
    try:
        difficulty = max(1, min(10, int(difficulty_raw)))
    except (TypeError, ValueError):
        difficulty = 4

    return {
        "id": qid,
        "domain": domain,
        "topic": topic[:120],
        "question": question_text,
        "options": {letter: option for letter, option in zip(LETTERS, options)},
        "answer": LETTERS[answer_index],
        "explanation": explanation,
        "difficulty": difficulty,
        "source_hint": source_hint[:300],
    }


def validate_question_pack(data: Any) -> list[dict[str, Any]]:
    """Validate a JSON question pack and reject malformed or duplicate ids."""
    if isinstance(data, list):
        raw_questions = data
    elif isinstance(data, dict) and isinstance(data.get("questions"), list):
        raw_questions = data["questions"]
    else:
        raise QuestionPackError("Expected a JSON object with a 'questions' list.")
    if not raw_questions:
        raise QuestionPackError("The question pack is empty.")
    if len(raw_questions) > MAX_IMPORTED_QUESTIONS:
        raise QuestionPackError(f"A pack can contain at most {MAX_IMPORTED_QUESTIONS:,} questions.")

    questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_questions, start=1):
        try:
            question = normalize_question(raw, fallback_id=f"import-{index}")
        except QuestionPackError as exc:
            raise QuestionPackError(f"Question {index}: {exc}") from exc
        if question["id"] in seen:
            raise QuestionPackError(f"Duplicate question id: {question['id']}")
        seen.add(question["id"])
        questions.append(question)
    return questions


def load_question_pack(path: str | Path) -> list[dict[str, Any]]:
    """Read and validate a learner-provided JSON question pack."""
    source = Path(path)
    try:
        if source.stat().st_size > MAX_IMPORT_BYTES:
            raise QuestionPackError("Question pack is larger than 10 MB.")
        data = json.loads(source.read_text(encoding="utf-8"))
    except QuestionPackError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QuestionPackError(f"Could not read question pack: {exc}") from exc
    return validate_question_pack(data)


def _format_number(value: int | float | Fraction) -> str:
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _numeric_distractors(correct: int, rng: random.Random, *, step: int | None = None) -> list[str]:
    gap = max(1, step or max(1, abs(correct) // 12))
    candidates = [correct + offset * gap for offset in (-3, -2, -1, 1, 2, 3, 4, -4)]
    candidates = [number for number in candidates if number >= 0 and number != correct]
    rng.shuffle(candidates)
    return [str(number) for number in candidates[:3]]


def _generated(
    qid: str,
    topic: str,
    question_text: str,
    answer: str,
    distractors: Iterable[str],
    explanation: str,
    rng: random.Random,
    difficulty: int = 3,
) -> dict[str, Any]:
    options = [str(answer), *(str(value) for value in distractors)]
    unique = []
    for option in options:
        if option not in unique and option != str(answer):
            unique.append(option)
    if len(unique) < 3:
        candidate = 1
        while len(unique) < 3:
            text = f"{answer} + {candidate}"
            if text != str(answer) and text not in unique:
                unique.append(text)
            candidate += 1
    values = [str(answer), *unique[:3]]
    rng.shuffle(values)
    return {
        "id": qid,
        "domain": "quantitative",
        "topic": topic,
        "question": question_text,
        "options": {letter: option for letter, option in zip(LETTERS, values)},
        "answer": LETTERS[values.index(str(answer))],
        "explanation": explanation,
        "difficulty": difficulty,
        "source_hint": "Generated practice problem; review the worked explanation.",
    }


def generate_aptitude_questions(
    rng: random.Random | None = None,
    *,
    per_topic: int = 6,
) -> list[dict[str, Any]]:
    """Create fresh, deterministic-when-seeded arithmetic and reasoning MCQs."""
    rng = rng or random.Random()
    serial = 0
    generated: list[dict[str, Any]] = []

    def add(topic: str, text: str, answer: int | str, distractors: Iterable[int | str], explanation: str, level: int = 3) -> None:
        nonlocal serial
        serial += 1
        generated.append(_generated(
            f"generated-{rng.getrandbits(48):012x}-{serial:03d}",
            topic,
            text,
            _format_number(answer) if isinstance(answer, (int, float, Fraction)) else str(answer),
            [_format_number(item) if isinstance(item, (int, float, Fraction)) else str(item) for item in distractors],
            explanation,
            rng,
            level,
        ))

    for _ in range(per_topic):
        # Numbers and basic operations.
        operation = rng.choice(("+", "−", "×", "÷"))
        if operation == "+":
            left, right = rng.randint(125, 980), rng.randint(25, 470)
            answer = left + right
        elif operation == "−":
            left, right = rng.randint(350, 1_200), rng.randint(25, 300)
            answer = left - right
        elif operation == "×":
            left, right = rng.randint(12, 39), rng.randint(3, 18)
            answer = left * right
        else:
            right, answer = rng.randint(3, 18), rng.randint(8, 80)
            left = right * answer
        add(
            "Numbers and Basic Operations",
            f"Calculate: {left} {operation} {right} = ?",
            answer,
            _numeric_distractors(answer, rng),
            f"Work the operation directly: {left} {operation} {right} = {answer}.",
            2,
        )

        # Percentages, with values chosen to produce whole-number answers.
        percentage = rng.choice((5, 10, 15, 20, 25, 30, 40, 50))
        base = rng.choice((100, 200, 240, 300, 400, 500, 600, 800, 1_000))
        answer = base * percentage // 100
        add(
            "Percentages",
            f"What is {percentage}% of {base}?",
            answer,
            _numeric_distractors(answer, rng),
            f"Convert {percentage}% to {percentage}/100 and multiply: {base} × {percentage}/100 = {answer}.",
            3,
        )

        # Profit/loss.
        cost = rng.randrange(200, 1_201, 100)
        profit_rate = rng.choice((10, 15, 20, 25, 30))
        profit = cost * profit_rate // 100
        selling_price = cost + profit
        add(
            "Profit and Loss",
            f"An article costs ₹{cost} and is sold at a {profit_rate}% profit. What is its selling price?",
            selling_price,
            _numeric_distractors(selling_price, rng, step=max(5, cost // 20)),
            f"Profit = {profit_rate}% of ₹{cost} = ₹{profit}. Selling price = cost + profit = ₹{selling_price}.",
            3,
        )

        # Simple interest.
        principal = rng.choice((1_000, 1_500, 2_000, 2_500, 3_000, 4_000, 5_000))
        rate = rng.choice((4, 5, 6, 8, 10, 12))
        years = rng.randint(1, 5)
        interest = principal * rate * years // 100
        add(
            "Simple Interest",
            f"Find the simple interest on ₹{principal} at {rate}% per year for {years} years.",
            interest,
            _numeric_distractors(interest, rng, step=max(5, interest // 10)),
            f"Simple interest = principal × rate × time / 100 = {principal} × {rate} × {years} / 100 = ₹{interest}.",
            4,
        )

        # Ratio and proportion.
        first, second = rng.randint(1, 6), rng.randint(2, 8)
        unit = rng.randint(4, 20)
        total = (first + second) * unit
        share = second * unit
        add(
            "Ratio and Proportion",
            f"A sum of ₹{total} is divided in the ratio {first}:{second}. How much is the second share?",
            share,
            _numeric_distractors(share, rng, step=max(2, unit)),
            f"Total ratio parts = {first} + {second} = {first + second}. Each part is ₹{unit}; the second share is {second} × ₹{unit} = ₹{share}.",
            4,
        )

        # Time, speed and distance.
        speed = rng.randint(25, 90)
        hours = rng.randint(2, 8)
        distance = speed * hours
        add(
            "Time, Speed and Distance",
            f"A vehicle travels at {speed} km/h for {hours} hours. How far does it travel?",
            distance,
            _numeric_distractors(distance, rng, step=max(5, speed // 2)),
            f"Distance = speed × time = {speed} × {hours} = {distance} km.",
            3,
        )

        # Work-rate questions with deliberately integral combined times.
        days_a, days_b = rng.choice(((4, 4), (6, 3), (8, 8), (12, 4), (10, 10), (18, 9)))
        days_together = days_a * days_b // (days_a + days_b)
        add(
            "Time and Work",
            f"A can finish a job in {days_a} days and B in {days_b} days. Working together at the same rates, how many days will they need?",
            f"{days_together} days",
            [f"{days_together + 1} days", f"{max(1, days_together - 1)} days", f"{days_a + days_b} days"],
            f"Their combined daily rate is 1/{days_a} + 1/{days_b} of the job. The time is {days_a} × {days_b} / ({days_a} + {days_b}) = {days_together} days.",
            5,
        )

        # Averages.
        average = rng.randint(45, 90)
        values = [average + rng.randint(-12, 12) for _ in range(4)]
        values[-1] = 4 * average - sum(values[:-1])
        add(
            "Average",
            f"Find the average of {', '.join(map(str, values))}.",
            average,
            _numeric_distractors(average, rng, step=2),
            f"Add the four values to get {sum(values)}, then divide by 4: the average is {average}.",
            3,
        )

        # Arithmetic progressions.
        first_term = rng.randint(3, 30)
        difference = rng.randint(2, 11)
        terms = [first_term + difference * index for index in range(4)]
        next_term = terms[-1] + difference
        add(
            "Number Series",
            f"What is the next number in this series: {', '.join(map(str, terms))}, ___?",
            next_term,
            [next_term + difference, next_term - difference, next_term + 2 * difference],
            f"Each term increases by {difference}; add {difference} to {terms[-1]} to get {next_term}.",
            3,
        )

        # Rectangle area.
        length, width = rng.randint(8, 30), rng.randint(3, 16)
        area = length * width
        add(
            "Mensuration",
            f"A rectangle is {length} cm long and {width} cm wide. What is its area?",
            area,
            _numeric_distractors(area, rng, step=max(2, width)),
            f"Area of a rectangle = length × width = {length} × {width} = {area} cm².",
            3,
        )

        # Letter-shift coding.
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        word = "".join(rng.choice(letters[:22]) for _ in range(3))
        shift = rng.choice((1, 2, 3))
        coded = "".join(letters[(letters.index(char) + shift) % 26] for char in word)
        wrong_codes = []
        for other_shift in (shift + 1, shift + 2, shift + 3):
            wrong_codes.append("".join(letters[(letters.index(char) + other_shift) % 26] for char in word))
        add(
            "Coding and Decoding",
            f"Each letter is moved forward by {shift} places in the alphabet. How is '{word}' coded?",
            coded,
            wrong_codes,
            f"Move each letter forward {shift} place(s): {word} becomes {coded}.",
            4,
        )

        # Odd-one-out: three perfect squares and one nearby non-square.
        root = rng.randint(4, 12)
        square_values = [root * root, (root + 1) ** 2, (root + 2) ** 2]
        odd_value = (root + 3) ** 2 + 1
        choices = [*square_values, odd_value]
        rng.shuffle(choices)
        add(
            "Classification and Odd One Out",
            f"Which number does not belong: {', '.join(map(str, choices))}?",
            odd_value,
            [str(value) for value in square_values],
            f"{square_values[0]}, {square_values[1]} and {square_values[2]} are perfect squares. {odd_value} is not.",
            4,
        )

    return generated


def build_question_pool(
    custom_questions: Iterable[dict[str, Any]] = (),
    *,
    rng: random.Random | None = None,
    aptitude_per_topic: int = 6,
) -> list[dict[str, Any]]:
    """Return a validated copy of the starter bank plus fresh aptitude items."""
    pool = [normalize_question(question) for question in SEED_QUESTIONS]
    pool.extend(generate_aptitude_questions(rng, per_topic=aptitude_per_topic))
    existing_ids = {question["id"] for question in pool}
    for index, raw in enumerate(custom_questions, start=1):
        question = normalize_question(raw, fallback_id=f"custom-{index}")
        if question["id"] in existing_ids:
            raise QuestionPackError(f"Custom question id conflicts with the starter bank: {question['id']}")
        existing_ids.add(question["id"])
        pool.append(question)
    return pool


def shuffle_question(question: dict[str, Any], rng: random.Random | None = None) -> dict[str, Any]:
    """Copy a question and randomise its options without changing the answer."""
    rng = rng or random.Random()
    shuffled = dict(question)
    pairs = list(question["options"].items())
    correct_text = question["options"][question["answer"]]
    rng.shuffle(pairs)
    shuffled["options"] = {letter: pair[1] for letter, pair in zip(LETTERS, pairs)}
    shuffled["answer"] = next(letter for letter, option in shuffled["options"].items() if option == correct_text)
    return shuffled
