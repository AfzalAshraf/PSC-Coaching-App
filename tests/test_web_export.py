import json
import unittest
from pathlib import Path

from psc_coach.catalog import DOMAIN_LABELS, TRACKS, track_domain_ids
from psc_coach.data.bank import SEED_QUESTIONS


ROOT = Path(__file__).resolve().parents[1]
WEB_DATA = ROOT / "web" / "data" / "starter-bank.json"


class WebExportTests(unittest.TestCase):
    def test_pwa_bank_matches_python_question_source(self):
        payload = json.loads(WEB_DATA.read_text(encoding="utf-8"))
        self.assertEqual(payload["schemaVersion"], 1)
        self.assertEqual([item["id"] for item in payload["questions"]], [item["id"] for item in SEED_QUESTIONS])
        self.assertEqual(payload["questions"], list(SEED_QUESTIONS))
        self.assertEqual(payload["domains"], DOMAIN_LABELS)

    def test_pwa_tracks_preserve_exam_blueprints_and_syllabus_links(self):
        payload = json.loads(WEB_DATA.read_text(encoding="utf-8"))
        self.assertEqual(set(payload["tracks"]), set(TRACKS))
        for track_id, track in TRACKS.items():
            exported = payload["tracks"][track_id]
            self.assertEqual(exported["weights"], dict(track.weights))
            self.assertEqual(exported["domainToBucket"], dict(track.domain_to_bucket))
            self.assertEqual(exported["availableDomains"], track_domain_ids(track_id))
            self.assertEqual(exported["officialUrl"], track.official_url)
            self.assertEqual(sum(exported["weights"].values()), 100)


if __name__ == "__main__":
    unittest.main()
