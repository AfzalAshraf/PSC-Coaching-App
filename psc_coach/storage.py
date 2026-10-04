"""Small, dependency-free, atomic JSON profile storage."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

PROFILE_VERSION = 2


def default_profile() -> dict[str, Any]:
    return {
        "schema_version": PROFILE_VERSION,
        "settings": {
            "track": "10th",
            "daily_goal_minutes": 45,
            "negative_marking": True,
        },
        "stats": {
            "sessions": 0,
            "questions": 0,
            "correct": 0,
            "streak": 0,
            "last_study_date": "",
            "domain_stats": {},
            "trend": [],
        },
        "sessions": [],
        "flashcards": [],
        "custom_questions": [],
        "daily_checks": {},
        "legacy_subject_scores": {},
    }


def default_profile_path() -> Path:
    """Choose a per-user writable directory on Windows, macOS or Linux."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "KeralaPSC Coach" / "profile.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "KeralaPSC Coach" / "profile.json"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "kerala-psc-coach" / "profile.json"


def _valid_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_profile(raw: Any) -> dict[str, Any]:
    """Merge missing fields into older profiles without discarding user data."""
    base = default_profile()
    if not isinstance(raw, dict):
        return base
    profile = copy.deepcopy(base)
    profile["schema_version"] = PROFILE_VERSION
    for key in ("settings", "stats"):
        value = raw.get(key)
        if isinstance(value, dict):
            profile[key].update(value)
    for key in ("sessions", "flashcards", "custom_questions"):
        profile[key] = _valid_list(raw.get(key))
    profile["daily_checks"] = raw.get("daily_checks") if isinstance(raw.get("daily_checks"), dict) else {}
    profile["legacy_subject_scores"] = (
        raw.get("legacy_subject_scores") if isinstance(raw.get("legacy_subject_scores"), dict) else {}
    )
    # Guard settings against invalid values from hand-edited or older files.
    try:
        profile["settings"]["daily_goal_minutes"] = max(10, min(240, int(profile["settings"].get("daily_goal_minutes", 45))))
    except (TypeError, ValueError):
        profile["settings"]["daily_goal_minutes"] = 45
    if profile["settings"].get("track") not in {"10th", "plus_two", "degree"}:
        profile["settings"]["track"] = "10th"
    profile["settings"]["negative_marking"] = bool(profile["settings"].get("negative_marking", True))
    stats = profile["stats"]
    for key in ("sessions", "questions", "correct", "streak"):
        try:
            stats[key] = max(0, int(stats.get(key, 0)))
        except (TypeError, ValueError):
            stats[key] = 0
    if not isinstance(stats.get("domain_stats"), dict):
        stats["domain_stats"] = {}
    stats["trend"] = _valid_list(stats.get("trend"))[-100:]
    stats["last_study_date"] = str(stats.get("last_study_date", ""))
    return profile


def migrate_legacy_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """Migrate the prior single-file simulator's local profile, if present."""
    profile = default_profile()
    try:
        profile["stats"]["sessions"] = max(0, int(raw.get("exams", 0)))
        profile["stats"]["questions"] = max(0, int(raw.get("qs", 0)))
        profile["stats"]["correct"] = max(0, int(raw.get("correct", 0)))
    except (TypeError, ValueError):
        pass

    old_scores = raw.get("scores", {}) if isinstance(raw.get("scores"), dict) else {}
    profile["legacy_subject_scores"] = copy.deepcopy(old_scores)
    name_map = {
        "polity": "constitution",
        "math": "quantitative",
        "science": "science_technology",
        "gk": "history",
        "english": "english",
        "malayalam": "malayalam",
    }
    for old_name, old_score in old_scores.items():
        if not isinstance(old_score, dict):
            continue
        domain = name_map.get(str(old_name).strip().lower())
        if not domain:
            continue
        try:
            total = max(0, int(old_score.get("t", 0)))
            correct = max(0, min(total, int(old_score.get("c", 0))))
        except (TypeError, ValueError):
            continue
        profile["stats"]["domain_stats"][domain] = {"total": total, "correct": correct}

    old_history = raw.get("hist", [])
    for item in _valid_list(old_history)[-50:]:
        if not isinstance(item, dict):
            continue
        try:
            count = max(0, int(item.get("n", 0)))
            correct = max(0, int(item.get("c", 0)))
            percentage = float(item.get("pct", 0))
        except (TypeError, ValueError):
            continue
        profile["sessions"].append({
            "date": str(item.get("date", "")),
            "track": "legacy",
            "count": count,
            "correct": correct,
            "wrong": max(0, count - correct),
            "skipped": 0,
            "score_pct": percentage,
            "elapsed_seconds": max(0, int(item.get("t", 0))),
        })
        profile["stats"]["trend"].append(percentage)

    old_cards = raw.get("flashcards", [])
    for index, old_card in enumerate(_valid_list(old_cards)[-300:], start=1):
        if not isinstance(old_card, dict):
            continue
        front = str(old_card.get("front") or old_card.get("question") or "").strip()
        answer = str(old_card.get("correct_answer") or old_card.get("back") or "").strip()
        if not front or not answer:
            continue
        fingerprint = hashlib.sha256(f"{front}|{answer}".encode("utf-8")).hexdigest()[:16]
        old_subject = str(old_card.get("subject", "")).strip().lower()
        domain = name_map.get(old_subject, "history")
        due = str(old_card.get("next_review", ""))
        if due and len(due) == 10:
            due += "T00:00:00"
        try:
            interval = max(0, int(old_card.get("interval", 1)))
            repetitions = max(0, int(old_card.get("reviews", 0)))
            ease = float(old_card.get("ease", 2.5))
        except (TypeError, ValueError):
            interval, repetitions, ease = 1, 0, 2.5
        profile["flashcards"].append({
            "id": f"legacy-{fingerprint}-{index}",
            "question": front,
            "answer": answer,
            "explanation": str(old_card.get("explanation", "")),
            "mnemonic": str(old_card.get("mnemonic", "")),
            "options": old_card.get("options", {}) if isinstance(old_card.get("options"), dict) else {},
            "domain": domain,
            "topic": str(old_card.get("subject", "Legacy review")),
            "next_review": due or datetime.now().isoformat(timespec="seconds"),
            "interval": interval,
            "repetitions": repetitions,
            "ease": max(1.3, ease),
            "added": str(old_card.get("added", "")),
        })

    last_history = profile["sessions"][-1]["date"] if profile["sessions"] else ""
    if last_history:
        profile["stats"]["last_study_date"] = last_history[:10]
    profile["schema_version"] = PROFILE_VERSION
    return normalize_profile(profile)


class ProfileStore:
    """Read/write learner data with atomic replacement to avoid partial files."""

    def __init__(self, path: str | Path | None = None, legacy_path: str | Path | None = None):
        self.path = Path(path) if path is not None else default_profile_path()
        self.legacy_path = (
            Path(legacy_path) if legacy_path is not None else Path.home() / ".kerala_psc_v11.json"
        )
        self.load_warning = ""
        self.migrated = False

    def load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                return normalize_profile(json.loads(self.path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                self.load_warning = f"Saved profile could not be read: {exc}"
                return default_profile()
        if self.legacy_path.exists():
            try:
                legacy = json.loads(self.legacy_path.read_text(encoding="utf-8"))
                if isinstance(legacy, dict):
                    self.migrated = True
                    profile = migrate_legacy_profile(legacy)
                    try:
                        self.save(profile)
                    except OSError as exc:
                        self.load_warning = f"Old profile loaded, but migration could not be saved: {exc}"
                    return profile
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                self.load_warning = f"Old profile could not be migrated: {exc}"
        return default_profile()

    def save(self, profile: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(normalize_profile(profile), ensure_ascii=False, indent=2)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.path)
        except OSError:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    def export_backup(self, profile: dict[str, Any], path: str | Path) -> None:
        """Write a portable profile backup without API credentials or secrets."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(normalize_profile(profile), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
