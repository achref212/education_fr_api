import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import LearningPath, LearningPathStep
from app.domain.ports import ILearningPathRepository
from app.infrastructure.models.learning_path import LearningPathORM
from app.infrastructure.models.learning_path_step import LearningPathStepORM
from app.infrastructure.models.user import UserORM


class SqlLearningPathRepository(ILearningPathRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_class_level(self, class_level: str) -> LearningPath | None:
        return self.get_default_for_class_level(class_level)

    def get_default_for_class_level(self, class_level: str) -> LearningPath | None:
        stmt = select(LearningPathORM).where(
            LearningPathORM.class_level == class_level,
            LearningPathORM.is_active.is_(True),
        ).order_by(
            LearningPathORM.is_default.desc(),
            LearningPathORM.created_at.asc(),
        )
        row = self._session.scalar(stmt)
        return _path_to_domain(row) if row else None

    def find_match(
        self, class_level: str, delf_level: str | None, score: int | None
    ) -> LearningPath | None:
        stmt = (
            select(LearningPathORM)
            .where(
                LearningPathORM.class_level == class_level,
                LearningPathORM.is_active.is_(True),
            )
            .order_by(
                LearningPathORM.is_default.desc(),
                LearningPathORM.min_score.desc().nullslast(),
                LearningPathORM.created_at.asc(),
            )
        )
        candidates = [_path_to_domain(r) for r in self._session.scalars(stmt).all()]
        if not candidates:
            return None

        same_level = [
            path for path in candidates if delf_level and path.delf_target_level == delf_level
        ]
        for bucket in (same_level, candidates):
            scored = [path for path in bucket if _score_matches(path, score)]
            if scored:
                return scored[0]
            unbounded = [
                path
                for path in bucket
                if path.min_score is None and path.max_score is None
            ]
            if unbounded:
                return unbounded[0]
        return candidates[0]

    def get(self, path_id: UUID) -> LearningPath | None:
        row = self._session.get(LearningPathORM, path_id)
        return _path_to_domain(row) if row else None

    def list_all(self) -> list[LearningPath]:
        stmt = select(LearningPathORM).order_by(
            LearningPathORM.class_level,
            LearningPathORM.delf_target_level,
            LearningPathORM.min_score.asc().nullsfirst(),
            LearningPathORM.created_at,
        )
        return [_path_to_domain(r) for r in self._session.scalars(stmt).all()]

    def count_steps(self, path_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(LearningPathStepORM)
            .where(LearningPathStepORM.path_id == path_id)
        )
        return int(self._session.scalar(stmt) or 0)

    def count_assigned_users(self, path_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(UserORM)
            .where(UserORM.assigned_learning_path_id == path_id)
        )
        return int(self._session.scalar(stmt) or 0)

    def list_steps(self, path_id: UUID) -> list[LearningPathStep]:
        stmt = (
            select(LearningPathStepORM)
            .where(LearningPathStepORM.path_id == path_id)
            .order_by(LearningPathStepORM.step_order)
        )
        return [_step_to_domain(r) for r in self._session.scalars(stmt).all()]

    def get_step(self, step_id: UUID) -> LearningPathStep | None:
        row = self._session.get(LearningPathStepORM, step_id)
        return _step_to_domain(row) if row else None

    def create_path(
        self,
        class_level: str,
        title: str,
        delf_target_level: str,
        description: str | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        is_default: bool = False,
    ) -> LearningPath:
        now = datetime.now(timezone.utc)
        row = LearningPathORM(
            id=uuid.uuid4(),
            class_level=class_level,
            title=title,
            description=description,
            delf_target_level=delf_target_level,
            is_active=True,
            min_score=min_score,
            max_score=max_score,
            is_default=is_default,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _path_to_domain(row)

    def update_path(
        self,
        path_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        delf_target_level: str | None = None,
        is_active: bool | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        is_default: bool | None = None,
    ) -> LearningPath | None:
        row = self._session.get(LearningPathORM, path_id)
        if row is None:
            return None
        if title is not None:
            row.title = title
        if description is not None:
            row.description = description
        if delf_target_level is not None:
            row.delf_target_level = delf_target_level
        if is_active is not None:
            row.is_active = is_active
        row.min_score = min_score
        row.max_score = max_score
        if is_default is not None:
            row.is_default = is_default
        self._session.flush()
        return _path_to_domain(row)

    def delete_path(self, path_id: UUID) -> bool:
        row = self._session.get(LearningPathORM, path_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def create_step(
        self,
        path_id: UUID,
        step_order: int,
        step_type: str,
        title: str,
        xp_reward: int,
        quiz_category: str | None = None,
        lesson_id: UUID | None = None,
        story_id: UUID | None = None,
        required_step_id: UUID | None = None,
    ) -> LearningPathStep:
        now = datetime.now(timezone.utc)
        row = LearningPathStepORM(
            id=uuid.uuid4(),
            path_id=path_id,
            step_order=step_order,
            step_type=step_type,
            title=title,
            xp_reward=xp_reward,
            quiz_category=quiz_category,
            lesson_id=lesson_id,
            story_id=story_id,
            required_step_id=required_step_id,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _step_to_domain(row)

    def update_step(
        self,
        step_id: UUID,
        *,
        step_order: int | None = None,
        step_type: str | None = None,
        title: str | None = None,
        xp_reward: int | None = None,
        quiz_category: str | None = None,
        lesson_id: UUID | None = None,
        story_id: UUID | None = None,
        required_step_id: UUID | None = None,
    ) -> LearningPathStep | None:
        row = self._session.get(LearningPathStepORM, step_id)
        if row is None:
            return None
        if step_order is not None:
            row.step_order = step_order
        if step_type is not None:
            row.step_type = step_type
        if title is not None:
            row.title = title
        if xp_reward is not None:
            row.xp_reward = xp_reward
        if quiz_category is not None:
            row.quiz_category = quiz_category
        if lesson_id is not None:
            row.lesson_id = lesson_id
        if story_id is not None:
            row.story_id = story_id
        if required_step_id is not None:
            row.required_step_id = required_step_id
        self._session.flush()
        return _step_to_domain(row)

    def delete_step(self, step_id: UUID) -> bool:
        row = self._session.get(LearningPathStepORM, step_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True


def _path_to_domain(row: LearningPathORM) -> LearningPath:
    return LearningPath(
        id=row.id,
        class_level=row.class_level,
        title=row.title,
        delf_target_level=row.delf_target_level,
        created_at=row.created_at,
        description=row.description,
        is_active=row.is_active,
        min_score=row.min_score,
        max_score=row.max_score,
        is_default=row.is_default,
    )


def _step_to_domain(row: LearningPathStepORM) -> LearningPathStep:
    return LearningPathStep(
        id=row.id,
        path_id=row.path_id,
        step_order=row.step_order,
        step_type=row.step_type,
        title=row.title,
        xp_reward=row.xp_reward,
        created_at=row.created_at,
        quiz_category=row.quiz_category,
        lesson_id=row.lesson_id,
        story_id=row.story_id,
        required_step_id=row.required_step_id,
    )


def _score_matches(path: LearningPath, score: int | None) -> bool:
    if score is None:
        return path.min_score is None and path.max_score is None
    if path.min_score is not None and score < path.min_score:
        return False
    if path.max_score is not None and score > path.max_score:
        return False
    return True
