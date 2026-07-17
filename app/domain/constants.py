"""Shared domain constants for parcours, difficulty, and multiplayer games."""

CLASS_LEVELS: tuple[str, ...] = (
    "2ème année",
    "3ème année",
    "4ème année",
    "5ème année",
    "6ème année",
    "7ème année",
    "8ème année",
    "9ème année",
)

DIFFICULTY_MODES: tuple[str, ...] = ("easy", "medium", "hard")

STEP_TYPES: tuple[str, ...] = ("lesson", "quiz", "story")

STEP_STATUSES: tuple[str, ...] = ("locked", "available", "in_progress", "completed")

SESSION_STATUS: tuple[str, ...] = (
    "waiting",
    "in_progress",
    "finished",
    "cancelled",
)

LESSON_CATEGORIES: tuple[str, ...] = (
    "Grammaire",
    "Conjugaison",
    "Orthographe",
    "Vocabulaire",
    "Lecture",
    "Dictée",
)

QUIZ_CATEGORIES: tuple[str, ...] = (
    "Grammaire",
    "Conjugaison",
    "Orthographe",
    "Vocabulaire",
)

DELF_TARGETS_BY_CLASS: dict[str, str] = {
    "2ème année": "A1.1",
    "3ème année": "A1",
    "4ème année": "A1",
    "5ème année": "A2",
    "6ème année": "A2",
    "7ème année": "A1",
    "8ème année": "A2",
    "9ème année": "B1",
}

MIN_STEP_SCORE_TO_UNLOCK: int = 60

BASE_XP_PER_STEP: int = 10
XP_BONUS_PER_SCORE_POINT: float = 0.2

DEFAULT_QUESTIONS_PER_GAME: int = 10
BASE_TIME_PER_QUESTION_MS: int = 30000

DIFFICULTY_CONFIG: dict[str, dict[str, float | int]] = {
    "easy": {
        "level_offset": 0,
        "time_multiplier": 1.5,
        "question_count_factor": 0.8,
        "score_multiplier": 1.0,
    },
    "medium": {
        "level_offset": 0,
        "time_multiplier": 1.0,
        "question_count_factor": 1.0,
        "score_multiplier": 1.2,
    },
    "hard": {
        "level_offset": 1,
        "time_multiplier": 0.75,
        "question_count_factor": 1.2,
        "score_multiplier": 1.5,
    },
}

USER_LEVEL_SCORE_MULTIPLIERS: dict[str, float] = {
    "debutant": 1.0,
    "intermediaire": 1.1,
    "avance": 1.2,
}

ALLOWED_DIFFICULTIES: tuple[str, ...] = DIFFICULTY_MODES

DELF_LEVELS: tuple[str, ...] = ("A1.1", "A1", "A2", "B1", "B2")

DELFT_TEST_STATUSES: tuple[str, ...] = ("in_progress", "completed", "abandoned")

DEFAULT_QUESTIONS_PER_CATEGORY: int = 5

DEFAULT_DELF_LEVEL_THRESHOLDS: list[dict[str, int | str]] = [
    {"level": "B2", "minOverall": 90, "minCategory": 85},
    {"level": "B1", "minOverall": 80, "minCategory": 70},
    {"level": "A2", "minOverall": 65, "minCategory": 55},
    {"level": "A1", "minOverall": 50, "minCategory": 40},
    {"level": "A1.1", "minOverall": 35, "minCategory": 25},
]
