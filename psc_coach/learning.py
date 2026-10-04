"""Pure learning, exam selection, scoring and spaced-review logic."""

from __future__ import annotations

import copy
import hashlib
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from .catalog import DOMAIN_LABELS, TRACKS, track_domain_ids
from .questions import shuffle_question
from .storage import normalize_profile


class NotEnoughQuestionsError(ValueError):
    """Raised when a requested drill cannot be made without repeating items."""


def allocate_quotas(count: int, weights: dict[str, int]) -> dict[str, int]:
    """Allocate an integer number of items using the largest-remainder method."""
    if count < 0:
        raise ValueError("count cannot be negative")
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("weights must have a positive total")
    exact = {key: count * weight / total_weight for key, weight in weights.items()}
    allocated = {key: int(value) for key, value in exact.items()}
    remaining = count - sum(allocated.values())
    order = sorted(weights, key=lambda key: (exact[key] - allocated[key], weights[key]), reverse=True)
    for key in order[:remaining]:
        allocated[key] += 1
    return allocated


def _accuracy(profile: dict[str, Any], domain: str) -> float | None:
    entry = profile.get("stats", {}).get("domain_stats", {}).get(domain, {})
    total = int(entry.get("total", 0) or 0)
    if total <= 0:
        return None
    return 100.0 * int(entry.get("correct", 0) or 0) / total


def _weighted_sample(
    candidates: list[dict[str, Any]],
    count: int,
    rng: random.Random,
    profile: dict[str, Any] | None = None,
    adaptive: bool = False,
) -> list[dict[str, Any]]:
    """Sample without replacement; adaptive practice favours weak domains."""
    remaining = list(candidates)
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < count:
        if adaptive and profile is not None:
            weights = []
            for question in remaining:
                accuracy = _accuracy(profile, question["domain"])
                weights.append(1.0 if accuracy is None else 1.0 + max(0.0, 75.0 - accuracy) / 15.0)
            chosen = rng.choices(remaining, weights=weights, k=1)[0]
        else:
            chosen = rng.choice(remaining)
        selected.append(chosen)
        remaining.remove(chosen)
    return selected


def select_questions(
    question_pool: Iterable[dict[str, Any]],
    track_id: str,
    count: int,
    *,
    domain: str | None = None,
    topic: str | None = None,
    rng: random.Random | None = None,
    adaptive: bool = False,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select unique questions and return their exam-blueprint coverage notes.

    Full mocks follow the selected track's mark weights as closely as the
    available bank allows. Missing buckets are filled from other eligible
    questions rather than duplicated, and the result carries a transparent note.
    """
    if track_id not in TRACKS:
        raise ValueError(f"Unknown exam track: {track_id}")
    if count < 1:
        raise ValueError("Choose at least one question.")
    rng = rng or random.Random()
    track = TRACKS[track_id]
    all_questions = list(question_pool)
    allowed_domains = set(track_domain_ids(track_id, include_supplementary=True))
    eligible = [question for question in all_questions if question.get("domain") in allowed_domains]
    core_eligible = [
        question for question in eligible
        if track.domain_to_bucket.get(question.get("domain")) in track.weights
    ]

    if domain:
        if domain not in DOMAIN_LABELS:
            raise ValueError(f"Unknown subject: {domain}")
        eligible = [question for question in eligible if question.get("domain") == domain]
    if topic:
        folded_topic = topic.strip().casefold()
        eligible = [question for question in eligible if str(question.get("topic", "")).casefold() == folded_topic]

    if not eligible:
        subject_name = DOMAIN_LABELS.get(domain or "", "this selection")
        raise NotEnoughQuestionsError(
            f"There are no {subject_name} questions in the local bank yet. "
            "Import a question pack or choose another subject."
        )
    if len(eligible) < count:
        raise NotEnoughQuestionsError(
            f"Only {len(eligible)} unique question(s) are available for this selection. "
            "Choose a shorter drill or import more questions; questions are never repeated in one session."
        )

    coverage_notes: list[str] = []
    chosen: list[dict[str, Any]] = []
    if domain is not None or topic is not None:
        chosen = _weighted_sample(eligible, count, rng, profile, adaptive)
    else:
        quotas = allocate_quotas(count, dict(track.weights))
        bucket_questions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for question in eligible:
            bucket = track.domain_to_bucket.get(question["domain"])
            if bucket in track.weights:
                bucket_questions[bucket].append(question)

        selected_ids: set[str] = set()
        shortages: list[tuple[str, int]] = []
        for bucket, quota in quotas.items():
            candidates = [q for q in bucket_questions.get(bucket, []) if q["id"] not in selected_ids]
            take = min(quota, len(candidates))
            sampled = _weighted_sample(candidates, take, rng, profile, adaptive)
            chosen.extend(sampled)
            selected_ids.update(q["id"] for q in sampled)
            if take < quota:
                shortages.append((bucket, quota - take))

        remaining = [q for q in core_eligible if q["id"] not in selected_ids]
        missing_places = count - len(chosen)
        if len(remaining) < missing_places:
            supplementary = [q for q in eligible if q["id"] not in selected_ids and q not in remaining]
            remaining.extend(supplementary)
        chosen.extend(_weighted_sample(remaining, missing_places, rng, profile, adaptive))
        if shortages:
            short_names = [track.bucket_labels.get(bucket, bucket) for bucket, _ in shortages]
            if "Current Affairs" in short_names:
                coverage_notes.append(
                    "No up-to-date Current Affairs questions are bundled. Import a dated, source-linked pack; "
                    "the missing places were rebalanced across the available syllabus topics."
                )
            other_short = [name for name in short_names if name != "Current Affairs"]
            if other_short:
                coverage_notes.append(
                    "The starter bank is lighter than the official blueprint in "
                    + ", ".join(other_short)
                    + "; those places were rebalanced across other available topics."
                )

    rng.shuffle(chosen)
    presented = [shuffle_question(question, rng) for question in chosen]
    if "current_affairs" in track.domain_to_bucket and not any(
        question.get("domain") == "current_affairs" for question in eligible
    ):
        note = (
            "The offline starter bank contains no up-to-date Current Affairs items. "
            "Import a dated, source-linked pack and use official sources for recent facts."
        )
        if note not in coverage_notes:
            coverage_notes.append(note)

    coverage = defaultdict(int)
    for question in presented:
        bucket = track.domain_to_bucket.get(question["domain"], "supplementary")
        coverage[bucket] += 1
    return {
        "questions": presented,
        "coverage": dict(coverage),
        "notes": coverage_notes,
        "requested": count,
    }


def grade_session(
    questions: Iterable[dict[str, Any]],
    answers: dict[str, str],
    *,
    penalty_per_wrong: float = 0.0,
) -> dict[str, Any]:
    """Score attempted and skipped questions and provide topic-level results."""
    questions = list(questions)
    if penalty_per_wrong < 0:
        raise ValueError("Penalty cannot be negative")
    correct = wrong = skipped = 0
    by_domain: dict[str, dict[str, Any]] = {}
    reviews: list[dict[str, Any]] = []
    for question in questions:
        qid = question["id"]
        user_answer = answers.get(qid, "")
        was_answered = bool(user_answer) and user_answer in "ABCD"
        is_correct = was_answered and user_answer == question["answer"]
        if not was_answered:
            skipped += 1
        elif is_correct:
            correct += 1
        else:
            wrong += 1
        domain = question["domain"]
        stats = by_domain.setdefault(domain, {"total": 0, "correct": 0, "wrong": 0, "skipped": 0})
        stats["total"] += 1
        stats["correct"] += int(is_correct)
        stats["wrong"] += int(was_answered and not is_correct)
        stats["skipped"] += int(not was_answered)
        reviews.append({
            "id": qid,
            "domain": domain,
            "topic": question.get("topic", ""),
            "question": question["question"],
            "options": dict(question["options"]),
            "correct_answer": question["answer"],
            "user_answer": user_answer,
            "was_correct": bool(is_correct),
            "explanation": question.get("explanation", ""),
            "source_hint": question.get("source_hint", ""),
        })

    total = len(questions)
    attempts = correct + wrong
    net_marks = correct - wrong * penalty_per_wrong
    score_pct = round(100.0 * net_marks / total, 1) if total else 0.0
    accuracy_pct = round(100.0 * correct / attempts, 1) if attempts else 0.0
    for stats in by_domain.values():
        stats["accuracy_pct"] = round(100.0 * stats["correct"] / stats["total"], 1) if stats["total"] else 0.0
    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "skipped": skipped,
        "attempted": attempts,
        "net_marks": round(net_marks, 2),
        "score_pct": score_pct,
        "accuracy_pct": accuracy_pct,
        "by_domain": dict(by_domain),
        "reviews": reviews,
    }


def _parse_datetime(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def due_flashcards(profile: dict[str, Any], now: datetime | None = None) -> list[dict[str, Any]]:
    """Return due flashcards in the order they should be reviewed."""
    now = _parse_datetime(now or datetime.now())
    due: list[dict[str, Any]] = []
    for card in profile.get("flashcards", []):
        try:
            next_review = _parse_datetime(card.get("next_review", "9999-12-31T23:59:59"))
        except (TypeError, ValueError):
            next_review = datetime.min
        if next_review <= now:
            due.append(card)
    due.sort(key=lambda card: str(card.get("next_review", "")))
    return due


def _card_fingerprint(question: dict[str, Any]) -> str:
    correct_text = question.get("options", {}).get(question.get("answer", ""), "")
    source = "|".join((
        question.get("domain", ""),
        question.get("question", "").strip().casefold(),
        str(correct_text).strip().casefold(),
    ))
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:20]


def update_after_session(
    profile: dict[str, Any],
    questions: Iterable[dict[str, Any]],
    answers: dict[str, str],
    *,
    track_id: str,
    elapsed_seconds: int,
    penalty_per_wrong: float = 0.0,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Update learner history and automatically create cards for errors."""
    questions = list(questions)
    now = now or datetime.now()
    now = _parse_datetime(now)
    result = grade_session(questions, answers, penalty_per_wrong=penalty_per_wrong)
    updated = normalize_profile(copy.deepcopy(profile))
    stats = updated["stats"]
    stats["sessions"] += 1
    stats["questions"] += result["total"]
    stats["correct"] += result["correct"]
    today = now.date()
    last_day = str(stats.get("last_study_date", ""))
    if last_day == today.isoformat():
        pass
    elif last_day:
        try:
            previous = date.fromisoformat(last_day)
            stats["streak"] = stats.get("streak", 0) + 1 if previous == today - timedelta(days=1) else 1
        except ValueError:
            stats["streak"] = 1
    else:
        stats["streak"] = 1
    stats["last_study_date"] = today.isoformat()

    domain_stats = stats.setdefault("domain_stats", {})
    for domain, entry in result["by_domain"].items():
        aggregate = domain_stats.setdefault(domain, {"total": 0, "correct": 0})
        aggregate["total"] = int(aggregate.get("total", 0)) + entry["total"]
        aggregate["correct"] = int(aggregate.get("correct", 0)) + entry["correct"]

    question_by_id = {question["id"]: question for question in questions}
    flashcards = updated["flashcards"]
    by_fingerprint = {card.get("id"): index for index, card in enumerate(flashcards)}
    for review in result["reviews"]:
        if review["was_correct"]:
            continue
        question = question_by_id[review["id"]]
        card_id = _card_fingerprint(question)
        answer_text = question["options"][question["answer"]]
        card = {
            "id": card_id,
            "question": question["question"],
            "answer": answer_text,
            "explanation": question.get("explanation", ""),
            "options": dict(question["options"]),
            "domain": question["domain"],
            "topic": question.get("topic", ""),
            "next_review": now.isoformat(timespec="seconds"),
            "interval": 0,
            "repetitions": 0,
            "ease": 2.5,
            "added": now.isoformat(timespec="seconds"),
        }
        if card_id in by_fingerprint:
            existing_index = by_fingerprint[card_id]
            flashcards[existing_index].update({
                "next_review": card["next_review"],
                "interval": 0,
                "repetitions": 0,
                "ease": max(1.3, float(flashcards[existing_index].get("ease", 2.5)) - 0.15),
            })
        else:
            flashcards.append(card)
            by_fingerprint[card_id] = len(flashcards) - 1

    session = {
        "date": now.isoformat(timespec="seconds"),
        "track": track_id,
        "count": result["total"],
        "correct": result["correct"],
        "wrong": result["wrong"],
        "skipped": result["skipped"],
        "net_marks": result["net_marks"],
        "score_pct": result["score_pct"],
        "accuracy_pct": result["accuracy_pct"],
        "elapsed_seconds": max(0, int(elapsed_seconds)),
        "penalty_per_wrong": penalty_per_wrong,
    }
    updated["sessions"].append(session)
    updated["sessions"] = updated["sessions"][-200:]
    stats["trend"].append({"date": now.date().isoformat(), "score_pct": result["score_pct"], "track": track_id})
    stats["trend"] = stats["trend"][-100:]
    return updated, result


def schedule_flashcard(
    profile: dict[str, Any],
    card_id: str,
    quality: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Schedule a card using a simple SM-2-inspired interval/ease model."""
    if quality not in {"again", "hard", "good", "easy"}:
        raise ValueError("quality must be one of: again, hard, good, easy")
    now = _parse_datetime(now or datetime.now())
    card = next((item for item in profile.get("flashcards", []) if item.get("id") == card_id), None)
    if card is None:
        raise KeyError(f"Flashcard not found: {card_id}")

    repetitions = max(0, int(card.get("repetitions", 0)))
    interval = max(0, int(card.get("interval", 0)))
    ease = max(1.3, float(card.get("ease", 2.5)))
    if quality == "again":
        repetitions = 0
        interval = 0
        ease = max(1.3, ease - 0.2)
        next_review = now + timedelta(minutes=10)
    elif quality == "hard":
        interval = max(1, round(max(1, interval) * 1.2))
        ease = max(1.3, ease - 0.15)
        next_review = now + timedelta(days=interval)
    elif quality == "good":
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 3
        else:
            interval = max(1, round(max(1, interval) * ease))
        repetitions += 1
        next_review = now + timedelta(days=interval)
    else:  # easy
        if repetitions == 0:
            interval = 4
        else:
            interval = max(2, round(max(1, interval) * ease * 1.3))
        repetitions += 1
        ease += 0.15
        next_review = now + timedelta(days=interval)

    card.update({
        "repetitions": repetitions,
        "interval": interval,
        "ease": round(ease, 2),
        "next_review": next_review.isoformat(timespec="seconds"),
        "last_review": now.isoformat(timespec="seconds"),
        "last_quality": quality,
    })
    return profile


def weak_domains(profile: dict[str, Any], *, minimum_questions: int = 3) -> list[tuple[str, float, int]]:
    """Return studied domains from weakest to strongest, excluding tiny samples."""
    values: list[tuple[str, float, int]] = []
    for domain, entry in profile.get("stats", {}).get("domain_stats", {}).items():
        total = int(entry.get("total", 0) or 0)
        if total < minimum_questions:
            continue
        correct = int(entry.get("correct", 0) or 0)
        values.append((domain, round(100.0 * correct / total, 1), total))
    return sorted(values, key=lambda item: (item[1], -item[2]))


def daily_plan(profile: dict[str, Any], track_id: str, today: date | None = None) -> list[dict[str, Any]]:
    """Create a practical, repeatable daily plan focused on active recall."""
    today = today or date.today()
    goal = int(profile.get("settings", {}).get("daily_goal_minutes", 45))
    goal = max(10, min(240, goal))
    reviews = len(due_flashcards(profile, datetime.combine(today, datetime.min.time())))
    weaker = weak_domains(profile)
    focused_domain = weaker[0][0] if weaker else "history"
    focus_name = DOMAIN_LABELS.get(focused_domain, focused_domain.replace("_", " ").title())
    if goal <= 15:
        review_minutes = goal // 3
        focus_minutes = goal // 3
    else:
        review_minutes = max(5, round(goal * 0.25))
        focus_minutes = max(5, round(goal * 0.45))
    quiz_minutes = max(1, goal - review_minutes - focus_minutes)
    # Keep the plan duration aligned with the selected daily target.
    if review_minutes + focus_minutes + quiz_minutes != goal:
        quiz_minutes = goal - review_minutes - focus_minutes
    return [
        {
            "id": "review",
            "title": f"Review {reviews} due flashcard{'s' if reviews != 1 else ''}" if reviews else "Review your saved mistakes",
            "detail": "Try to recall the answer before revealing it.",
            "minutes": review_minutes,
            "action": "flashcards",
        },
        {
            "id": "focus",
            "title": f"Strengthen {focus_name}",
            "detail": "Study one small topic, then explain it from memory.",
            "minutes": focus_minutes,
            "action": "practice",
            "domain": focused_domain,
        },
        {
            "id": "quiz",
            "title": "Take a short mixed quiz",
            "detail": f"Use the {TRACKS[track_id].short_name} blueprint and review every explanation.",
            "minutes": quiz_minutes,
            "action": "practice",
        },
    ]


def task_completion(profile: dict[str, Any], day: date | None = None) -> dict[str, bool]:
    day = day or date.today()
    checks = profile.get("daily_checks", {}).get(day.isoformat(), {})
    if not isinstance(checks, dict):
        return {}
    return {str(key): bool(value) for key, value in checks.items()}


def set_task_completion(profile: dict[str, Any], task_id: str, completed: bool, day: date | None = None) -> None:
    day = day or date.today()
    checks = profile.setdefault("daily_checks", {}).setdefault(day.isoformat(), {})
    checks[task_id] = bool(completed)
    # Keep only a short checklist history in the profile.
    for old_day in sorted(profile["daily_checks"])[:-45]:
        profile["daily_checks"].pop(old_day, None)
