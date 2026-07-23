import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.entities import Lesson, User
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

    def list_by_professor(self, professor_id: UUID) -> list[Lesson]:
        stmt = (
            select(LessonORM)
            .where(LessonORM.professor_id == professor_id)
            .order_by(LessonORM.sort_order, LessonORM.created_at.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def list_visible_for_user(self, user: User) -> list[Lesson]:
        stmt = (
            select(LessonORM)
            .where(_visible_filter(user))
            .order_by(LessonORM.sort_order, LessonORM.created_at.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def list_by_level(self, level: str) -> list[Lesson]:
        stmt = (
            select(LessonORM)
            .where(LessonORM.level == level)
            .order_by(LessonORM.sort_order, LessonORM.created_at.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def list_by_category(
        self, category: str, user: User | None = None
    ) -> list[Lesson]:
        filters = [LessonORM.category == category]
        if user is not None:
            filters.append(_visible_filter(user))
        stmt = (
            select(LessonORM)
            .where(*filters)
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
        professor_id: UUID | None = None,
        school_id: UUID | None = None,
        visibility: str = "public",
    ) -> Lesson:
        now = datetime.now(timezone.utc)
        row = LessonORM(
            id=uuid.uuid4(),
            title=title,
            content=content,
            category=category,
            level=level,
            sort_order=sort_order,
            professor_id=professor_id,
            school_id=school_id,
            visibility=visibility,
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
        school_id: UUID | None = None,
        visibility: str | None = None,
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
        if school_id is not None:
            row.school_id = school_id
        if visibility is not None:
            row.visibility = visibility
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
        professor_id=row.professor_id,
        school_id=row.school_id,
        visibility=row.visibility or "public",
    )


def _visible_filter(user: User):
    if user.role in {"admin", "prof"}:
        return True
    school_id = user.school_id
    return or_(
        LessonORM.visibility == "public",
        LessonORM.school_id == school_id,
    )
