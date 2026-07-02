import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import QuizQuestion
from app.domain.ports import IQuizRepository
from app.infrastructure.models.quiz_question import QuizQuestionORM


class SqlQuizRepository(IQuizRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[QuizQuestion]:
        stmt = select(QuizQuestionORM)
        rows = self._session.scalars(stmt).all()
        return [_to_domain(r) for r in rows]

    def list_by_level(self, level: str) -> list[QuizQuestion]:
        stmt = select(QuizQuestionORM).where(QuizQuestionORM.level == level)
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def get(self, question_id: UUID) -> QuizQuestion | None:
        row = self._session.get(QuizQuestionORM, question_id)
        return _to_domain(row) if row else None

    def create(
        self,
        question: str,
        options: list[Any],
        correct_index: int,
        explanation: str | None,
        category: str,
        level: str,
    ) -> QuizQuestion:
        row = QuizQuestionORM(
            id=uuid.uuid4(),
            question=question,
            options=list(options),
            correct_index=correct_index,
            explanation=explanation,
            category=category,
            level=level,
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def update(
        self,
        question_id: UUID,
        *,
        question: str | None = None,
        options: list[Any] | None = None,
        correct_index: int | None = None,
        explanation: str | None = None,
        category: str | None = None,
        level: str | None = None,
    ) -> QuizQuestion | None:
        row = self._session.get(QuizQuestionORM, question_id)
        if row is None:
            return None
        if question is not None:
            row.question = question
        if options is not None:
            row.options = list(options)
        if correct_index is not None:
            row.correct_index = correct_index
        if explanation is not None:
            row.explanation = explanation
        if category is not None:
            row.category = category
        if level is not None:
            row.level = level
        self._session.flush()
        return _to_domain(row)

    def delete(self, question_id: UUID) -> bool:
        row = self._session.get(QuizQuestionORM, question_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def count(self) -> int:
        return int(
            self._session.scalar(
                select(func.count()).select_from(QuizQuestionORM)
            )
            or 0
        )


def _to_domain(row: QuizQuestionORM) -> QuizQuestion:
    return QuizQuestion(
        id=row.id,
        question=row.question,
        options=list(row.options) if row.options else [],
        correct_index=row.correct_index,
        explanation=row.explanation,
        category=row.category,
        level=row.level,
    )
