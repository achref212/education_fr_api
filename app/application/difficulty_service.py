import math

from app.domain.constants import (
    BASE_TIME_PER_QUESTION_MS,
    CLASS_LEVELS,
    DEFAULT_QUESTIONS_PER_GAME,
    DIFFICULTY_CONFIG,
    USER_LEVEL_SCORE_MULTIPLIERS,
)


class DifficultyService:
    def resolve_question_level(self, class_level: str, difficulty: str) -> str:
        config = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["medium"])
        offset = int(config["level_offset"])
        if class_level not in CLASS_LEVELS:
            return class_level
        index = CLASS_LEVELS.index(class_level)
        target_index = min(index + offset, len(CLASS_LEVELS) - 1)
        return CLASS_LEVELS[target_index]

    def resolve_question_count(
        self, base_count: int, difficulty: str
    ) -> int:
        config = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["medium"])
        factor = float(config["question_count_factor"])
        return max(3, int(math.ceil(base_count * factor)))

    def resolve_time_limit_ms(self, difficulty: str) -> int:
        config = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["medium"])
        multiplier = float(config["time_multiplier"])
        return int(BASE_TIME_PER_QUESTION_MS * multiplier)

    def resolve_score_multiplier(
        self, difficulty: str, user_level: str
    ) -> float:
        config = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["medium"])
        difficulty_multiplier = float(config["score_multiplier"])
        user_multiplier = USER_LEVEL_SCORE_MULTIPLIERS.get(user_level, 1.0)
        return difficulty_multiplier * user_multiplier

    def build_game_settings(self, difficulty: str) -> dict[str, int]:
        return {
            "timeLimitMs": self.resolve_time_limit_ms(difficulty),
            "questionCount": self.resolve_question_count(
                DEFAULT_QUESTIONS_PER_GAME, difficulty
            ),
        }
