from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from psc_coach.storage import (
    ProfileStore,
    default_profile,
    default_profile_path,
    migrate_legacy_profile,
    normalize_profile,
)


class ProfileStorageTests(unittest.TestCase):
    def test_profile_round_trip_preserves_unicode_and_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nested" / "profile.json"
            store = ProfileStore(path=path, legacy_path=Path(temporary) / "missing-old-profile.json")
            profile = default_profile()
            profile["settings"]["track"] = "plus_two"
            profile["custom_questions"] = [{"id": "q-ml", "question": "മലയാളം"}]
            profile["stats"]["questions"] = 12
            store.save(profile)
            loaded = store.load()
        self.assertEqual(loaded["settings"]["track"], "plus_two")
        self.assertEqual(loaded["custom_questions"][0]["question"], "മലയാളം")
        self.assertEqual(loaded["stats"]["questions"], 12)

    def test_bad_profile_is_nonfatal_and_reports_a_warning(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "profile.json"
            path.write_text("{ not json", encoding="utf-8")
            store = ProfileStore(path=path, legacy_path=Path(temporary) / "absent.json")
            profile = store.load()
        self.assertEqual(profile["stats"]["questions"], 0)
        self.assertIn("could not be read", store.load_warning)

    def test_legacy_profile_migrates_without_retaining_api_key(self):
        old = {
            "provider": "gemini",
            "api_key": "must-not-be-copied",
            "exams": 4,
            "qs": 42,
            "correct": 31,
            "scores": {"Math": {"t": 12, "c": 8}, "GK": {"t": 10, "c": 5}},
            "hist": [{"date": "2025-01-01 10:20", "n": 10, "c": 7, "pct": 70, "t": 600}],
            "flashcards": [{
                "front": "A sample question?",
                "back": "Answer plus hint",
                "correct_answer": "42",
                "subject": "Math",
                "next_review": "2025-01-02",
                "interval": 1,
                "reviews": 2,
            }],
        }
        migrated = migrate_legacy_profile(old)
        self.assertEqual(migrated["stats"]["sessions"], 4)
        self.assertEqual(migrated["stats"]["questions"], 42)
        self.assertEqual(migrated["stats"]["domain_stats"]["quantitative"]["correct"], 8)
        self.assertEqual(migrated["flashcards"][0]["question"], "A sample question?")
        self.assertNotIn("api_key", migrated)

    def test_store_auto_migrates_legacy_file_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            current = folder / "new" / "profile.json"
            old = folder / "old.json"
            old.write_text(json.dumps({"exams": 1, "qs": 3, "correct": 2}), encoding="utf-8")
            store = ProfileStore(path=current, legacy_path=old)
            profile = store.load()
            self.assertTrue(store.migrated)
            self.assertTrue(current.exists())
            store_again = ProfileStore(path=current, legacy_path=old)
            profile_again = store_again.load()
        self.assertEqual(profile["stats"]["questions"], 3)
        self.assertFalse(store_again.migrated)
        self.assertEqual(profile_again["stats"]["correct"], 2)

    def test_profile_normalization_clamps_bad_user_preferences(self):
        profile = normalize_profile({
            "settings": {"track": "not-a-track", "daily_goal_minutes": 9999},
            "stats": {"questions": -12},
        })
        self.assertEqual(profile["settings"]["track"], "10th")
        self.assertEqual(profile["settings"]["daily_goal_minutes"], 240)
        self.assertEqual(profile["stats"]["questions"], 0)

    def test_default_profile_path_is_user_scoped(self):
        self.assertIn("psc", str(default_profile_path()).lower())


if __name__ == "__main__":
    unittest.main()
