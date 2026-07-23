import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import DelfMockAttempt
from app.domain.ports import IDelfMockAttemptRepository
from app.infrastructure.models.delf_mock_exam import DelfMockAttemptORM


class SqlDelfMockAttemptRepository(IDelfMockAttemptRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_attempt(
        self,
        *,
        user_id: UUID,
        exam_id: UUID,
    ) -> DelfMockAttempt:
        now = datetime.now(timezone.utc)
        row = DelfMockAttemptORM(
            id=uuid.uuid4(),
            user_id=user_id,
            exam_id=exam_id,
            status="in_progress",
            answers=[],
            section_scores={},
            approximate=True,
            started_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def get_attempt(self, attempt_id: UUID) -> DelfMockAttempt | None:
        row = self._session.get(DelfMockAttemptORM, attempt_id)
        return _to_domain(row) if row else None

    def get_active_attempt(
        self,
        *,
        user_id: UUID,
        exam_id: UUID,
    ) -> DelfMockAttempt | None:
        row = self._session.scalar(
            select(DelfMockAttemptORM)
            .where(
                DelfMockAttemptORM.user_id == user_id,
                DelfMockAttemptORM.exam_id == exam_id,
                DelfMockAttemptORM.status == "in_progress",
            )
            .order_by(DelfMockAttemptORM.created_at.desc())
            .limit(1)
        )
        return _to_domain(row) if row else None

    def update_attempt(
        self,
        attempt_id: UUID,
        *,
        status: str | None = None,
        answers: list[dict] | None = None,
        section_scores: dict[str, int] | None = None,
        overall_score: int | None = None,
        approximate: bool | None = None,
        finished_at: datetime | None = None,
    ) -> DelfMockAttempt | None:
        row = self._session.get(DelfMockAttemptORM, attempt_id)
        if row is None:
            return None
        if status is not None:
            row.status = status
        if answers is not None:
            row.answers = list(answers)
        if section_scores is not None:
            row.section_scores = dict(section_scores)
        if overall_score is not None:
            row.overall_score = overall_score
        if approximate is not None:
            row.approximate = approximate
        if finished_at is not None:
            row.finished_at = finished_at
        row.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return _to_domain(row)


def _to_domain(row: DelfMockAttemptORM) -> DelfMockAttempt:
    return DelfMockAttempt(
        id=row.id,
        user_id=row.user_id,
        exam_id=row.exam_id,
        status=row.status,
        answers=list(row.answers or []),
        section_scores={str(k): int(v) for k, v in dict(row.section_scores or {}).items()},
        overall_score=row.overall_score,
        approximate=row.approximate,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
