"""Kerala PSC exam tracks and syllabus-aware subject catalogue.

The mark distributions are transcribed from the linked Kerala PSC syllabus
notices. Post-specific notifications can differ, so the app treats these as
preparation blueprints rather than a promise of an exact future paper.
"""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ExamTrack:
    id: str
    name: str
    short_name: str
    description: str
    duration_minutes: int
    weights: Mapping[str, int]
    domain_to_bucket: Mapping[str, str]
    bucket_labels: Mapping[str, str]
    official_url: str
    syllabus_note: str

    @property
    def total_marks(self) -> int:
        return sum(self.weights.values())


DOMAIN_LABELS: dict[str, str] = {
    "history": "History",
    "geography": "Geography",
    "economics": "Economics",
    "civics": "Civics & Public Administration",
    "constitution": "Indian Constitution",
    "arts": "Arts, Literature, Culture & Sports",
    "biology": "Biology & Public Health",
    "physics_chemistry": "Physics & Chemistry",
    "science_technology": "Science & Technology",
    "computer": "Computer Science & IT",
    "current_affairs": "Current Affairs",
    "quantitative": "Arithmetic & Mental Ability",
    "english": "General English",
    "malayalam": "Malayalam",
    "tamil": "Tamil",
    "kannada": "Kannada",
}

LANGUAGE_DOMAINS = ("malayalam", "tamil", "kannada")

TRACKS: dict[str, ExamTrack] = {
    "10th": ExamTrack(
        id="10th",
        name="10th Level / LDC",
        short_name="10th Level",
        description=(
            "Common preliminary foundation for LDC and other posts accepting "
            "10th-level qualifications. Build Kerala and Indian GK, science, "
            "arithmetic and mental ability."
        ),
        duration_minutes=75,
        weights={"knowledge": 60, "science": 20, "quantitative": 20},
        domain_to_bucket={
            "history": "knowledge",
            "geography": "knowledge",
            "economics": "knowledge",
            "civics": "knowledge",
            "constitution": "knowledge",
            "arts": "knowledge",
            "current_affairs": "knowledge",
            "biology": "science",
            "physics_chemistry": "science",
            "science_technology": "science",
            "quantitative": "quantitative",
        },
        bucket_labels={
            "knowledge": "General Knowledge, Current Affairs & Kerala Renaissance",
            "science": "General Science",
            "quantitative": "Simple Arithmetic & Mental Ability",
        },
        official_url="https://www.keralapsc.gov.in/sites/default/files/inline-files/10th_level.pdf",
        syllabus_note=(
            "The official 10th-level common preliminary syllabus allocates "
            "60 marks to General Knowledge, Current Affairs and Renaissance "
            "in Kerala, 20 to General Science, and 20 to Simple Arithmetic "
            "and Mental Ability. Post-specific LDC tests may add other topics."
        ),
    ),
    "plus_two": ExamTrack(
        id="plus_two",
        name="Plus Two Level",
        short_name="Plus Two",
        description=(
            "Common preliminary practice across history, geography, civics, "
            "economics, constitution, sciences, computer science, languages "
            "and aptitude."
        ),
        duration_minutes=75,
        weights={
            "history": 5,
            "geography": 5,
            "civics": 5,
            "economics": 5,
            "constitution": 5,
            "biology": 5,
            "physics_chemistry": 5,
            "computer": 5,
            "arts": 5,
            "current_affairs": 5,
            "quantitative": 20,
            "english": 20,
            "regional_language": 10,
        },
        domain_to_bucket={
            "history": "history",
            "geography": "geography",
            "civics": "civics",
            "economics": "economics",
            "constitution": "constitution",
            "biology": "biology",
            "physics_chemistry": "physics_chemistry",
            "science_technology": "physics_chemistry",
            "computer": "computer",
            "arts": "arts",
            "current_affairs": "current_affairs",
            "quantitative": "quantitative",
            "english": "english",
            "malayalam": "regional_language",
            "tamil": "regional_language",
            "kannada": "regional_language",
        },
        bucket_labels={
            "history": "History",
            "geography": "Geography",
            "civics": "Civics & Public Administration",
            "economics": "Economics",
            "constitution": "Indian Constitution",
            "biology": "Biology",
            "physics_chemistry": "Physics & Chemistry",
            "computer": "Computer Science",
            "arts": "Arts, Sports & Literature",
            "current_affairs": "Current Affairs",
            "quantitative": "Simple Arithmetic & Mental Ability",
            "english": "General English",
            "regional_language": "Regional Language",
        },
        official_url=(
            "https://www.keralapsc.gov.in/sites/default/files/inline-files/"
            "syllabus_plus_two_level_preliminary_exam_2022.pdf"
        ),
        syllabus_note=(
            "The linked Kerala PSC Plus Two common preliminary syllabus shows "
            "the mark split used here. Check the notification for the post and "
            "exam cycle you are applying for."
        ),
    ),
    "degree": ExamTrack(
        id="degree",
        name="Degree Level",
        short_name="Degree",
        description=(
            "Degree-level common preliminary foundation with larger shares for "
            "arithmetic, reasoning and English, plus general knowledge and language."
        ),
        duration_minutes=75,
        weights={
            "history": 10,
            "geography": 5,
            "economics": 5,
            "civics": 5,
            "constitution": 5,
            "arts": 10,
            "computer": 5,
            "science_technology": 5,
            "quantitative": 20,
            "english": 20,
            "regional_language": 10,
        },
        domain_to_bucket={
            "history": "history",
            "geography": "geography",
            "economics": "economics",
            "civics": "civics",
            "constitution": "constitution",
            "arts": "arts",
            "computer": "computer",
            "biology": "science_technology",
            "physics_chemistry": "science_technology",
            "science_technology": "science_technology",
            "current_affairs": "arts",
            "quantitative": "quantitative",
            "english": "english",
            "malayalam": "regional_language",
            "tamil": "regional_language",
            "kannada": "regional_language",
        },
        bucket_labels={
            "history": "History",
            "geography": "Geography",
            "economics": "Economics",
            "civics": "Civics",
            "constitution": "Indian Constitution",
            "arts": "Arts, Literature, Culture & Sports",
            "computer": "Basics of Computer",
            "science_technology": "Science & Technology",
            "quantitative": "Simple Arithmetic, Mental Ability & Reasoning",
            "english": "General English",
            "regional_language": "Regional Language",
        },
        official_url=(
            "https://www.keralapsc.gov.in/sites/default/files/2025-01/"
            "degree_level_preliminary_revised_latest_.pdf"
        ),
        syllabus_note=(
            "Based on the revised Degree Level Common Preliminary syllabus "
            "and mark distribution published by Kerala PSC in 2025. Check the "
            "current post notification for the official syllabus."
        ),
    ),
}

CURRENT_AFFAIRS_SOURCES: tuple[tuple[str, str], ...] = (
    ("Kerala PSC notifications & syllabus", "https://www.keralapsc.gov.in/"),
    ("Government of Kerala", "https://kerala.gov.in/"),
    ("Press Information Bureau", "https://pib.gov.in/"),
)


def track_domain_ids(track_id: str, *, include_supplementary: bool = True) -> list[str]:
    """Return the syllabus domains available for the selected track."""
    track = TRACKS[track_id]
    domains = list(track.domain_to_bucket)
    if include_supplementary and track_id == "10th":
        domains.extend(("computer", "english", *LANGUAGE_DOMAINS))
    # Put domains in the same predictable order throughout the UI.
    return [domain for domain in DOMAIN_LABELS if domain in domains]


def domain_bucket(track_id: str, domain: str) -> str | None:
    """Return the exam blueprint bucket for a domain, if one exists."""
    return TRACKS[track_id].domain_to_bucket.get(domain)
