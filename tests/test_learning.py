from __future__ import annotations

import random
import unittest
from datetime import date, datetime, timedelta

from psc_coach.catalog import TRACKS
from psc_coach.learning import (
    NotEnoughQuestionsError,
    allocate_quotas,
    daily_plan,
    due_flashcards,
    grade_session,
    schedule_flashcard,
    select_questions,
    update_after_session,
    weak_domains,
)
from psc_coach.questions import build_question_pool, generate_aptitude_questions
from psc_coach.storage import default_profile


class CatalogueAndSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = build_question_pool(rng=random.Random(91))

    def test_all_official_blueprints_total_100(self):
        for track in TRACKS.values():
            self.assertEqual(track.total_marks, 100, track.id)

    def test_degree_mock_has_unique_questions_and_expected_core_quota(self):
        result = select_questions(self.pool, "degree", 100, rng=random.Random(17))
        questions = result["questions"]
        self.assertEqual(len(questions), 100)
        self.assertEqual(len({question["id"] for question in questions}), 100)
        self.assertEqual(result["coverage"]["quantitative"], 20)
        self.assertEqual(result["coverage"]["english"], 20)
        self.assertEqual(result["coverage"]["history"], 10)
        self.assertEqual(result["coverage"]["arts"], 10)
        self.assertTrue(any("Current Affairs" in note for note in result["notes"]))

    def test_plus_two_mock_discloses_missing_current_affairs(self):
        result = select_questions(self.pool, "plus_two", 100, rng=random.Random(19))
        self.assertEqual(len(result["questions"]), 100)
        self.assertEqual(len({question["id"] for question in result["questions"]}), 100)
        self.assertEqual(result["coverage"]["english"], 20)
        self.assertTrue(any("Current Affairs" in note for note in result["notes"]))

    def test_tenth_level_mock_uses_its_three_official_groups(self):
        result = select_questions(self.pool, "10th", 100, rng=random.Random(23))
        self.assertEqual(result["coverage"]["knowledge"], 60)
        self.assertEqual(result["coverage"]["science"], 20)
        self.assertEqual(result["coverage"]["quantitative"], 20)
        self.assertTrue(any("Current Affairs" in note for note in result["notes"]))
        self.assertFalse(any(question["domain"] in {"english", "computer", "malayalam"} for question in result["questions"]))

    def test_subject_filter_does_not_repeat_and_missing_current_affairs_is_clear(self):
        result = select_questions(self.pool, "degree", 10, domain="english", rng=random.Random(3))
        self.assertEqual(len(result["questions"]), 10)
        self.assertTrue(all(question["domain"] == "english" for question in result["questions"]))
        with self.assertRaises(NotEnoughQuestionsError):
            select_questions(self.pool, "degree", 5, domain="current_affairs", rng=random.Random(4))

    def test_imported_current_affairs_questions_fill_plus_two_quota(self):
        pack = [{
            "id": f"ca-2026-{index}",
            "domain": "current_affairs",
            "topic": "Verified 2026 update",
            "question": f"Which option is the correct dated fact, item {index}?",
            "options": ["Verified answer", "Distractor one", "Distractor two", "Distractor three"],
            "answer": "A",
            "explanation": "Check the linked official release.",
            "source_hint": "Official publisher; publication date: 2026-09-01",
        } for index in range(1, 6)]
        pool = build_question_pool(pack, rng=random.Random(7))
        result = select_questions(pool, "plus_two", 100, rng=random.Random(8))
        self.assertEqual(result["coverage"]["current_affairs"], 5)
        self.assertFalse(any("Current Affairs" in note for note in result["notes"]))

    def test_largest_remainder_quota_allocation(self):
        quotas = allocate_quotas(17, {"a": 60, "b": 20, "c": 20})
        self.assertEqual(sum(quotas.values()), 17)
        self.assertEqual(quotas, {"a": 10, "b": 4, "c": 3})

    def test_aptitude_generation_is_seedable_and_correct_answer_is_present(self):
        first = generate_aptitude_questions(random.Random(42), per_topic=2)
        second = generate_aptitude_questions(random.Random(42), per_topic=2)
        self.assertEqual([item["question"] for item in first], [item["question"] for item in second])
        self.assertEqual(len(first), 24)
        for question in first:
            self.assertEqual(len(question["options"]), 4)
            self.assertIn(question["answer"], question["options"])
            self.assertEqual(len(set(question["options"].values())), 4)
            self.assertTrue(question["explanation"])
        self.assertTrue(all(question["mnemonic"] for question in first))


class ScoringAndReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = build_question_pool(rng=random.Random(5))
        cls.questions = select_questions(cls.pool, "degree", 5, domain="history", rng=random.Random(7))["questions"]

    def test_scoring_counts_wrong_blank_and_negative_marks(self):
        first, second, third = self.questions[:3]
        wrong_letter = next(letter for letter in "ABCD" if letter != second["answer"])
        answers = {first["id"]: first["answer"], second["id"]: wrong_letter}
        result = grade_session(self.questions, answers, penalty_per_wrong=1 / 3)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["wrong"], 1)
        self.assertEqual(result["skipped"], 3)
        self.assertEqual(result["attempted"], 2)
        self.assertEqual(result["score_pct"], 13.3)
        self.assertNotEqual(result["reviews"][0]["id"], third["id"])

    def test_blank_answer_is_not_treated_as_an_attempt(self):
        result = grade_session(self.questions, {self.questions[0]["id"]: ""})
        self.assertEqual(result["skipped"], 5)
        self.assertEqual(result["wrong"], 0)
        self.assertEqual(result["attempted"], 0)

    def test_wrong_answers_become_due_flashcards(self):
        wrong_question = self.questions[0]
        answers = {wrong_question["id"]: "B" if wrong_question["answer"] != "B" else "C"}
        profile, result = update_after_session(
            default_profile(),
            self.questions,
            answers,
            track_id="degree",
            elapsed_seconds=75,
            penalty_per_wrong=1 / 3,
            now=datetime(2025, 1, 1, 12, 0, 0),
        )
        self.assertEqual(result["wrong"], 1)
        self.assertEqual(profile["stats"]["sessions"], 1)
        self.assertEqual(profile["stats"]["questions"], 5)
        self.assertEqual(len(profile["flashcards"]), 5)
        self.assertEqual(len(due_flashcards(profile, datetime(2025, 1, 1, 12, 1, 0))), 5)
        self.assertEqual(weak_domains(profile, minimum_questions=1)[0][1], 0.0)

    def test_streak_continues_only_on_consecutive_calendar_days(self):
        profile = default_profile()
        q = self.questions[:1]
        correct_answers = {q[0]["id"]: q[0]["answer"]}
        profile, _ = update_after_session(profile, q, correct_answers, track_id="10th", elapsed_seconds=5, now=datetime(2025, 1, 1, 9))
        profile, _ = update_after_session(profile, q, correct_answers, track_id="10th", elapsed_seconds=5, now=datetime(2025, 1, 2, 9))
        self.assertEqual(profile["stats"]["streak"], 2)
        profile, _ = update_after_session(profile, q, correct_answers, track_id="10th", elapsed_seconds=5, now=datetime(2025, 1, 5, 9))
        self.assertEqual(profile["stats"]["streak"], 1)

    def test_memory_hook_is_retained_in_answer_review_and_flashcard(self):
        question = dict(self.questions[0])
        question["mnemonic"] = "Divide by the bottom, multiply by the top."
        profile, result = update_after_session(
            default_profile(), [question], {}, track_id="degree", elapsed_seconds=8,
            now=datetime(2025, 4, 1, 9, 0, 0),
        )
        self.assertEqual(result["reviews"][0]["mnemonic"], question["mnemonic"])
        self.assertEqual(profile["flashcards"][0]["mnemonic"], question["mnemonic"])

    def test_card_schedule_advances_and_again_is_due_soon(self):
        profile, _ = update_after_session(
            default_profile(),
            self.questions[:1],
            {},
            track_id="degree",
            elapsed_seconds=12,
            now=datetime(2025, 3, 1, 10, 0, 0),
        )
        card_id = profile["flashcards"][0]["id"]
        schedule_flashcard(profile, card_id, "good", now=datetime(2025, 3, 1, 10, 0, 0))
        self.assertEqual(profile["flashcards"][0]["interval"], 1)
        self.assertEqual(len(due_flashcards(profile, datetime(2025, 3, 1, 10, 1, 0))), 0)
        self.assertEqual(len(due_flashcards(profile, datetime(2025, 3, 2, 10, 0, 0))), 1)
        schedule_flashcard(profile, card_id, "again", now=datetime(2025, 3, 2, 10, 0, 0))
        self.assertEqual(len(due_flashcards(profile, datetime(2025, 3, 2, 10, 11, 0))), 1)

    def test_daily_plan_has_three_active_recall_tasks(self):
        plan = daily_plan(default_profile(), "plus_two", date(2025, 6, 1))
        self.assertEqual([task["id"] for task in plan], ["review", "focus", "quiz"])
        self.assertEqual(sum(task["minutes"] for task in plan), 45)
        self.assertTrue(all(task["minutes"] > 0 for task in plan))


if __name__ == "__main__":
    unittest.main()
