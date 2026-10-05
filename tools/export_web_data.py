"""Export source-of-truth PSC catalog and starter questions for the PWA."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psc_coach.catalog import DOMAIN_LABELS, TRACKS, track_domain_ids
from psc_coach.data.bank import SEED_QUESTIONS

OUTPUT = ROOT / "web" / "data" / "starter-bank.json"


def export() -> None:
    tracks = {}
    for track_id, track in TRACKS.items():
        tracks[track_id] = {
            "id": track.id,
            "name": track.name,
            "shortName": track.short_name,
            "description": track.description,
            "durationMinutes": track.duration_minutes,
            "weights": dict(track.weights),
            "domainToBucket": dict(track.domain_to_bucket),
            "bucketLabels": dict(track.bucket_labels),
            "officialUrl": track.official_url,
            "syllabusNote": track.syllabus_note,
            "availableDomains": track_domain_ids(track_id),
        }

    payload = {
        "schemaVersion": 1,
        "domains": DOMAIN_LABELS,
        "tracks": tracks,
        "questions": list(SEED_QUESTIONS),
        "disclaimer": (
            "Original offline practice examples, not official Kerala PSC questions or a past-paper archive."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(SEED_QUESTIONS)} questions to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    export()
