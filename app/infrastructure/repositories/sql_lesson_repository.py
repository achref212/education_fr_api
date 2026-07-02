import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import Lesson
from app.domain.ports import ILessonRepository
from app.infrastructure.models.lesson import LessonORM


class SqlLessonRepository(ILessonRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Lesson]:
        stmt = select(LessonORM).order_by(
            LessonORM.sort_order, LessonORM.created_at.desc()
        )
        rows = self._session.scalars(stmt).all()
        return [_to_domain(r) for r in rows]

    def list_by_level(self, level: str) -> list[Lesson]:
        stmt = (
            select(LessonORM)
            .where(LessonORM.level == level)
            .order_by(LessonORM.sort_order, LessonORM.created_at.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def list_by_category(self, category: str) -> list[Lesson]:
        stmt = (
            select(LessonORM)
            .where(LessonORM.category == category)
            .order_by(LessonORM.sort_order, LessonORM.created_at.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def get(self, lesson_id: UUID) -> Lesson | None:
        row = self._session.get(LessonORM, lesson_id)
        return _to_domain(row) if row else None

    def create(
        self,
        title: str,
        content: str,
        category: str,
        level: str,
        sort_order: int,
    ) -> Lesson:
        now = datetime.now(timezone.utc)
        row = LessonORM(
            id=uuid.uuid4(),
            title=title,
            content=content,
            category=category,
            level=level,
            sort_order=sort_order,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def update(
        self,
        lesson_id: UUID,
        *,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        level: str | None = None,
        sort_order: int | None = None,
    ) -> Lesson | None:
        row = self._session.get(LessonORM, lesson_id)
        if row is None:
            return None
        if title is not None:
            row.title = title
        if content is not None:
            row.content = content
        if category is not None:
            row.category = category
        if level is not None:
            row.level = level
        if sort_order is not None:
            row.sort_order = sort_order
        self._session.flush()
        return _to_domain(row)

    def delete(self, lesson_id: UUID) -> bool:
        row = self._session.get(LessonORM, lesson_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def count(self) -> int:
        return int(
            self._session.scalar(select(func.count()).select_from(LessonORM)) or 0
        )

    def count_by_category(self) -> dict[str, int]:
        rows = self._session.execute(
            select(LessonORM.category, func.count())
            .group_by(LessonORM.category)
        ).all()
        return {str(cat): int(c) for cat, c in rows}


def _to_domain(row: LessonORM) -> Lesson:
    return Lesson(
        id=row.id,
        title=row.title,
        content=row.content,
        category=row.category,
        level=row.level,
        sort_order=row.sort_order,
        created_at=row.created_at,
    )
