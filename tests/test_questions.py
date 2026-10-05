from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path

from psc_coach.questions import (
    QuestionPackError,
    build_question_pool,
    load_question_pack,
    normalize_question,
    shuffle_question,
    validate_question_pack,
)


class QuestionBankTests(unittest.TestCase):
    def test_starter_bank_is_large_enough_for_practice_and_full_mocks(self):
        pool = build_question_pool(rng=random.Random(2))
        self.assertGreaterEqual(len(pool), 200)
        ids = [question["id"] for question in pool]
        self.assertEqual(len(ids), len(set(ids)))
        for question in pool:
            self.assertEqual(set(question["options"]), set("ABCD"))
            self.assertIn(question["answer"], question["options"])
            self.assertEqual(len(set(question["options"].values())), 4)

    def test_option_shuffle_keeps_correct_answer_text(self):
        question = normalize_question({
            "id": "sample-1",
            "domain": "history",
            "topic": "Sample",
            "question": "Which option is correct?",
            "options": ["Correct", "Wrong 1", "Wrong 2", "Wrong 3"],
            "answer": 0,
            "explanation": "Explanation.",
        })
        shuffled = shuffle_question(question, random.Random(3))
        self.assertEqual(shuffled["options"][shuffled["answer"]], "Correct")
        self.assertEqual(set(shuffled["options"].values()), set(question["options"].values()))

    def test_import_pack_accepts_letter_and_exact_text_answers(self):
        pack = {
            "version": 1,
            "questions": [
                {
                    "id": "pack-1",
                    "domain": "current_affairs",
                    "topic": "Sample update",
                    "question": "Which source is named?",
                    "options": {"A": "Official report", "B": "Blog", "C": "Rumour", "D": "Advertisement"},
                    "answer": "A",
                    "explanation": "Use a traceable official source.",
                    "mnemonic": "Source and date travel together.",
                    "source_hint": "Dated example source, 2025-01.",
                },
                {
                    "id": "pack-2",
                    "domain": "malayalam",
                    "topic": "Vocabulary",
                    "question": "Choose the correct word.",
                    "options": ["one", "two", "three", "four"],
                    "answer": "three",
                },
            ],
        }
        validated = validate_question_pack(pack)
        self.assertEqual(len(validated), 2)
        self.assertEqual(validated[0]["answer"], "A")
        self.assertEqual(validated[0]["mnemonic"], "Source and date travel together.")
        self.assertEqual(validated[1]["answer"], "C")

    def test_bad_packs_are_rejected_with_useful_errors(self):
        with self.assertRaisesRegex(QuestionPackError, "four"):
            validate_question_pack({"questions": [{"id": "bad", "domain": "history", "question": "Q", "options": ["A"], "answer": "A"}]})
        with self.assertRaisesRegex(QuestionPackError, "Unknown domain"):
            normalize_question({
                "id": "bad-domain", "domain": "unlisted", "question": "Q",
                "options": ["A", "B", "C", "D"], "answer": "A",
            })
        with self.assertRaisesRegex(QuestionPackError, "source_hint"):
            normalize_question({
                "id": "stale-current-affairs", "domain": "current_affairs", "question": "Q?",
                "options": ["A", "B", "C", "D"], "answer": "A",
            })
        with self.assertRaisesRegex(QuestionPackError, "Duplicate"):
            validate_question_pack({"questions": [
                {"id": "same", "domain": "history", "question": "Q1", "options": ["A", "B", "C", "D"], "answer": "A"},
                {"id": "same", "domain": "history", "question": "Q2", "options": ["A", "B", "C", "D"], "answer": "A"},
            ]})

    def test_file_question_pack_loads_from_disk(self):
        pack = {"questions": [{
            "id": "file-1", "domain": "geography", "topic": "Maps", "question": "Q?",
            "options": ["A", "B", "C", "D"], "answer": 2,
        }]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pack.json"
            path.write_text(json.dumps(pack), encoding="utf-8")
            question = load_question_pack(path)[0]
        self.assertEqual(question["answer"], "C")


if __name__ == "__main__":
    unittest.main()
