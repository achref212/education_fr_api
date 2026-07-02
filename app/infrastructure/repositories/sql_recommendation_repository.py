import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Recommendation
from app.domain.ports import IRecommendationRepository
from app.infrastructure.models.recommendation import RecommendationORM


class SqlRecommendationRepository(IRecommendationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        student_id: UUID,
        professor_id: UUID,
        content: str,
    ) -> Recommendation:
        row = RecommendationORM(
            id=uuid.uuid4(),
            student_id=student_id,
            professor_id=professor_id,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def list_for_student(self, student_id: UUID) -> list[Recommendation]:
        stmt = (
            select(RecommendationORM)
            .where(RecommendationORM.student_id == student_id)
            .order_by(RecommendationORM.created_at.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]


def _to_domain(row: RecommendationORM) -> Recommendation:
    return Recommendation(
        id=row.id,
        student_id=row.student_id,
        professor_id=row.professor_id,
        content=row.content,
        created_at=row.created_at,
    )
