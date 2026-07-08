from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.domain.constants import BASE_XP_PER_STEP, XP_BONUS_PER_SCORE_POINT
from app.domain.entities import StudentStats
from app.domain.ports import IStudentProgressRepository
from app.infrastructure.repositories.sql_student_progress_repository import (
    create_default_stats,
)


class StudentStatsService:
    def __init__(self, progress_repo: IStudentProgressRepository) -> None:
        self._progress = progress_repo

    def get_or_create(self, user_id: UUID) -> StudentStats:
        stats = self._progress.get_stats(user_id)
        if stats is not None:
            return stats
        default = create_default_stats(user_id)
        return self._progress.upsert_stats(default)

    def set_preferred_difficulty(
        self, user_id: UUID, difficulty: str
    ) -> StudentStats:
        stats = self.get_or_create(user_id)
        updated = StudentStats(
            user_id=stats.user_id,
            total_xp=stats.total_xp,
            current_streak=stats.current_streak,
            longest_streak=stats.longest_streak,
            preferred_difficulty=difficulty,
            updated_at=datetime.now(timezone.utc),
            last_activity_date=stats.last_activity_date,
        )
        return self._progress.upsert_stats(updated)

    def record_activity(
        self, user_id: UUID, xp_earned: int, activity_date: date | None = None
    ) -> StudentStats:
        stats = self.get_or_create(user_id)
        today = activity_date or datetime.now(timezone.utc).date()
        current_streak = stats.current_streak
        if stats.last_activity_date is None:
            current_streak = 1
        elif stats.last_activity_date == today:
            pass
        elif stats.last_activity_date == today - timedelta(days=1):
            current_streak += 1
        else:
            current_streak = 1
        longest_streak = max(stats.longest_streak, current_streak)
        updated = StudentStats(
            user_id=stats.user_id,
            total_xp=stats.total_xp + xp_earned,
            current_streak=current_streak,
            longest_streak=longest_streak,
            preferred_difficulty=stats.preferred_difficulty,
            updated_at=datetime.now(timezone.utc),
            last_activity_date=today,
        )
        return self._progress.upsert_stats(updated)

    def calculate_step_xp(self, base_xp: int, score: int) -> int:
        bonus = int(score * XP_BONUS_PER_SCORE_POINT)
        return base_xp + bonus

    def calculate_default_step_xp(self, score: int) -> int:
        return self.calculate_step_xp(BASE_XP_PER_STEP, score)
