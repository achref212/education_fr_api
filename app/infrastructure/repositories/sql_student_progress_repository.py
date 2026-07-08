import uuid
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import StudentStats, StudentStepProgress
from app.domain.ports import IStudentProgressRepository
from app.infrastructure.models.student_stats import StudentStatsORM
from app.infrastructure.models.student_step_progress import StudentStepProgressORM


class SqlStudentProgressRepository(IStudentProgressRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_stats(self, user_id: UUID) -> StudentStats | None:
        row = self._session.get(StudentStatsORM, user_id)
        return _stats_to_domain(row) if row else None

    def upsert_stats(self, stats: StudentStats) -> StudentStats:
        row = self._session.get(StudentStatsORM, stats.user_id)
        if row is None:
            row = StudentStatsORM(
                user_id=stats.user_id,
                total_xp=stats.total_xp,
                current_streak=stats.current_streak,
                longest_streak=stats.longest_streak,
                last_activity_date=stats.last_activity_date,
                preferred_difficulty=stats.preferred_difficulty,
                updated_at=stats.updated_at,
            )
            self._session.add(row)
        else:
            row.total_xp = stats.total_xp
            row.current_streak = stats.current_streak
            row.longest_streak = stats.longest_streak
            row.last_activity_date = stats.last_activity_date
            row.preferred_difficulty = stats.preferred_difficulty
            row.updated_at = stats.updated_at
        self._session.flush()
        return _stats_to_domain(row)

    def get_step_progress(
        self, user_id: UUID, step_id: UUID
    ) -> StudentStepProgress | None:
        stmt = select(StudentStepProgressORM).where(
            StudentStepProgressORM.user_id == user_id,
            StudentStepProgressORM.step_id == step_id,
        )
        row = self._session.scalar(stmt)
        return _progress_to_domain(row) if row else None

    def list_step_progress(self, user_id: UUID) -> list[StudentStepProgress]:
        stmt = select(StudentStepProgressORM).where(
            StudentStepProgressORM.user_id == user_id
        )
        return [_progress_to_domain(r) for r in self._session.scalars(stmt).all()]

    def upsert_step_progress(
        self, progress: StudentStepProgress
    ) -> StudentStepProgress:
        existing = self.get_step_progress(progress.user_id, progress.step_id)
        if existing is None:
            row = StudentStepProgressORM(
                id=progress.id if progress.id else uuid.uuid4(),
                user_id=progress.user_id,
                step_id=progress.step_id,
                status=progress.status,
                score=progress.score,
                attempts=progress.attempts,
                completed_at=progress.completed_at,
                updated_at=progress.updated_at,
            )
            self._session.add(row)
        else:
            row = self._session.scalar(
                select(StudentStepProgressORM).where(
                    StudentStepProgressORM.user_id == progress.user_id,
                    StudentStepProgressORM.step_id == progress.step_id,
                )
            )
            assert row is not None
            row.status = progress.status
            row.score = progress.score
            row.attempts = progress.attempts
            row.completed_at = progress.completed_at
            row.updated_at = progress.updated_at
        self._session.flush()
        return _progress_to_domain(row)


def _stats_to_domain(row: StudentStatsORM) -> StudentStats:
    return StudentStats(
        user_id=row.user_id,
        total_xp=row.total_xp,
        current_streak=row.current_streak,
        longest_streak=row.longest_streak,
        preferred_difficulty=row.preferred_difficulty,
        updated_at=row.updated_at,
        last_activity_date=row.last_activity_date,
    )


def _progress_to_domain(row: StudentStepProgressORM) -> StudentStepProgress:
    return StudentStepProgress(
        id=row.id,
        user_id=row.user_id,
        step_id=row.step_id,
        status=row.status,
        attempts=row.attempts,
        updated_at=row.updated_at,
        score=row.score,
        completed_at=row.completed_at,
    )


def create_default_stats(user_id: UUID) -> StudentStats:
    now = datetime.now(timezone.utc)
    return StudentStats(
        user_id=user_id,
        total_xp=0,
        current_streak=0,
        longest_streak=0,
        preferred_difficulty="medium",
        updated_at=now,
        last_activity_date=None,
    )
