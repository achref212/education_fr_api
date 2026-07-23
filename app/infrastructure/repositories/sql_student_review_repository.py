import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import StudentReviewItem
from app.domain.ports import IStudentReviewRepository
from app.infrastructure.models.student_review_item import StudentReviewItemORM


class SqlStudentReviewRepository(IStudentReviewRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_wrong_answer(
        self,
        *,
        user_id: UUID,
        source_type: str,
        source_id: str | None,
        question_id: str | None,
        category: str,
        question: str,
        options: list,
        selected_index: int | None,
        correct_index: int | None,
        explanation: str | None,
    ) -> StudentReviewItem:
        now = datetime.now(timezone.utc)
        row = self._find_existing(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            question_id=question_id,
        )
        if row is None:
            row = StudentReviewItemORM(
                id=uuid.uuid4(),
                user_id=user_id,
                source_type=source_type,
                source_id=source_id,
                question_id=question_id,
                category=category,
                question=question,
                options=list(options),
                selected_index=selected_index,
                correct_index=correct_index,
                explanation=explanation,
                status="open",
                times_reviewed=0,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.category = category
            row.question = question
            row.options = list(options)
            row.selected_index = selected_index
            row.correct_index = correct_index
            row.explanation = explanation
            row.status = "open"
            row.updated_at = now
        self._session.flush()
        return _to_domain(row)

    def list_for_user(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> list[StudentReviewItem]:
        stmt = select(StudentReviewItemORM).where(StudentReviewItemORM.user_id == user_id)
        if status is not None:
            stmt = stmt.where(StudentReviewItemORM.status == status)
        stmt = stmt.order_by(
            StudentReviewItemORM.status.asc(),
            StudentReviewItemORM.updated_at.desc(),
        )
        return [_to_domain(row) for row in self._session.scalars(stmt).all()]

    def get_for_user(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> StudentReviewItem | None:
        row = self._session.scalar(
            select(StudentReviewItemORM).where(
                StudentReviewItemORM.id == item_id,
                StudentReviewItemORM.user_id == user_id,
            )
        )
        return _to_domain(row) if row else None

    def mark_completed(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> StudentReviewItem | None:
        row = self._session.scalar(
            select(StudentReviewItemORM).where(
                StudentReviewItemORM.id == item_id,
                StudentReviewItemORM.user_id == user_id,
            )
        )
        if row is None:
            return None
        now = datetime.now(timezone.utc)
        if row.status == "completed":
            return _to_domain(row)
        row.status = "completed"
        row.times_reviewed += 1
        row.last_reviewed_at = now
        row.updated_at = now
        self._session.flush()
        return _to_domain(row)

    def _find_existing(
        self,
        *,
        user_id: UUID,
        source_type: str,
        source_id: str | None,
        question_id: str | None,
    ) -> StudentReviewItemORM | None:
        return self._session.scalar(
            select(StudentReviewItemORM).where(
                StudentReviewItemORM.user_id == user_id,
                StudentReviewItemORM.source_type == source_type,
                StudentReviewItemORM.source_id == source_id,
                StudentReviewItemORM.question_id == question_id,
            )
        )


def _to_domain(row: StudentReviewItemORM) -> StudentReviewItem:
    return StudentReviewItem(
        id=row.id,
        user_id=row.user_id,
        source_type=row.source_type,
        source_id=row.source_id,
        question_id=row.question_id,
        category=row.category,
        question=row.question,
        options=list(row.options or []),
        selected_index=row.selected_index,
        correct_index=row.correct_index,
        explanation=row.explanation,
        status=row.status,
        times_reviewed=row.times_reviewed,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_reviewed_at=row.last_reviewed_at,
    )
