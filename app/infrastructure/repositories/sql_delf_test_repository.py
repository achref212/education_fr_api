import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.constants import DEFAULT_DELF_LEVEL_THRESHOLDS, DEFAULT_QUESTIONS_PER_CATEGORY
from app.domain.entities import DelfTestConfig, DelfTestSession, DelfTestTemplate
from app.domain.ports import IDelfTestRepository
from app.infrastructure.models.delf_test import (
    DelfTestConfigORM,
    DelfTestSessionORM,
    DelfTestTemplateORM,
)


class SqlDelfTestRepository(IDelfTestRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_session(
        self,
        user_id: UUID,
        class_level: str,
        target_delf_level: str,
        question_ids_by_category: dict[str, list[str]],
    ) -> DelfTestSession:
        now = datetime.now(timezone.utc)
        row = DelfTestSessionORM(
            id=uuid.uuid4(),
            user_id=user_id,
            class_level=class_level,
            target_delf_level=target_delf_level,
            status="in_progress",
            question_ids_by_category=dict(question_ids_by_category),
            answers=[],
            category_scores={},
            started_at=now,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _session_to_domain(row)

    def get_session(self, session_id: UUID) -> DelfTestSession | None:
        row = self._session.get(DelfTestSessionORM, session_id)
        return _session_to_domain(row) if row else None

    def get_active_session(self, user_id: UUID) -> DelfTestSession | None:
        stmt = (
            select(DelfTestSessionORM)
            .where(
                DelfTestSessionORM.user_id == user_id,
                DelfTestSessionORM.status == "in_progress",
            )
            .order_by(DelfTestSessionORM.created_at.desc())
            .limit(1)
        )
        row = self._session.scalar(stmt)
        return _session_to_domain(row) if row else None

    def update_session(
        self,
        session_id: UUID,
        *,
        status: str | None = None,
        answers: list[dict[str, Any]] | None = None,
        category_scores: dict[str, int] | None = None,
        overall_score: int | None = None,
        achieved_delf_level: str | None = None,
        finished_at: datetime | None = None,
    ) -> DelfTestSession | None:
        row = self._session.get(DelfTestSessionORM, session_id)
        if row is None:
            return None
        if status is not None:
            row.status = status
        if answers is not None:
            row.answers = list(answers)
        if category_scores is not None:
            row.category_scores = dict(category_scores)
        if overall_score is not None:
            row.overall_score = overall_score
        if achieved_delf_level is not None:
            row.achieved_delf_level = achieved_delf_level
        if finished_at is not None:
            row.finished_at = finished_at
        self._session.flush()
        return _session_to_domain(row)

    def list_sessions_for_user(self, user_id: UUID) -> list[DelfTestSession]:
        stmt = (
            select(DelfTestSessionORM)
            .where(DelfTestSessionORM.user_id == user_id)
            .order_by(DelfTestSessionORM.created_at.desc())
        )
        return [_session_to_domain(r) for r in self._session.scalars(stmt).all()]

    def list_all_sessions(
        self,
        *,
        user_id: UUID | None = None,
        class_level: str | None = None,
        status: str | None = None,
    ) -> list[DelfTestSession]:
        stmt = select(DelfTestSessionORM)
        if user_id is not None:
            stmt = stmt.where(DelfTestSessionORM.user_id == user_id)
        if class_level is not None:
            stmt = stmt.where(DelfTestSessionORM.class_level == class_level)
        if status is not None:
            stmt = stmt.where(DelfTestSessionORM.status == status)
        stmt = stmt.order_by(DelfTestSessionORM.created_at.desc())
        return [_session_to_domain(r) for r in self._session.scalars(stmt).all()]

    def get_config(self) -> DelfTestConfig:
        row = self._session.scalar(select(DelfTestConfigORM).limit(1))
        if row is None:
            return _default_config()
        return _config_to_domain(row)

    def update_config(
        self,
        *,
        questions_per_category: int | None = None,
        level_thresholds: list[dict[str, int | str]] | None = None,
    ) -> DelfTestConfig:
        row = self._session.scalar(select(DelfTestConfigORM).limit(1))
        now = datetime.now(timezone.utc)
        if row is None:
            row = DelfTestConfigORM(
                id=uuid.uuid4(),
                questions_per_category=questions_per_category or DEFAULT_QUESTIONS_PER_CATEGORY,
                level_thresholds=list(level_thresholds or DEFAULT_DELF_LEVEL_THRESHOLDS),
                updated_at=now,
            )
            self._session.add(row)
        else:
            if questions_per_category is not None:
                row.questions_per_category = questions_per_category
            if level_thresholds is not None:
                row.level_thresholds = list(level_thresholds)
            row.updated_at = now
        self._session.flush()
        return _config_to_domain(row)

    def list_templates(self) -> list[DelfTestTemplate]:
        stmt = select(DelfTestTemplateORM).order_by(
            DelfTestTemplateORM.class_level.asc(),
            DelfTestTemplateORM.updated_at.desc(),
        )
        return [_template_to_domain(r) for r in self._session.scalars(stmt).all()]

    def get_template(self, template_id: UUID) -> DelfTestTemplate | None:
        row = self._session.get(DelfTestTemplateORM, template_id)
        return _template_to_domain(row) if row else None

    def get_active_template_for_class(self, class_level: str) -> DelfTestTemplate | None:
        stmt = (
            select(DelfTestTemplateORM)
            .where(
                DelfTestTemplateORM.class_level == class_level,
                DelfTestTemplateORM.is_active.is_(True),
            )
            .order_by(DelfTestTemplateORM.updated_at.desc())
            .limit(1)
        )
        row = self._session.scalar(stmt)
        return _template_to_domain(row) if row else None

    def create_template(
        self,
        *,
        name: str,
        description: str | None,
        class_level: str,
        target_delf_level: str,
        is_active: bool,
        question_ids_by_category: dict[str, list[str]],
    ) -> DelfTestTemplate:
        now = datetime.now(timezone.utc)
        if is_active:
            self._deactivate_templates_for_class(class_level)
        row = DelfTestTemplateORM(
            id=uuid.uuid4(),
            name=name,
            description=description,
            class_level=class_level,
            target_delf_level=target_delf_level,
            is_active=is_active,
            question_ids_by_category=dict(question_ids_by_category),
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _template_to_domain(row)

    def update_template(
        self,
        template_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        class_level: str | None = None,
        target_delf_level: str | None = None,
        is_active: bool | None = None,
        question_ids_by_category: dict[str, list[str]] | None = None,
    ) -> DelfTestTemplate | None:
        row = self._session.get(DelfTestTemplateORM, template_id)
        if row is None:
            return None
        next_class_level = class_level if class_level is not None else row.class_level
        if is_active is True:
            self._deactivate_templates_for_class(next_class_level, exclude_id=template_id)
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        if class_level is not None:
            row.class_level = class_level
        if target_delf_level is not None:
            row.target_delf_level = target_delf_level
        if is_active is not None:
            row.is_active = is_active
        if question_ids_by_category is not None:
            row.question_ids_by_category = dict(question_ids_by_category)
        row.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return _template_to_domain(row)

    def _deactivate_templates_for_class(
        self, class_level: str, exclude_id: UUID | None = None
    ) -> None:
        stmt = select(DelfTestTemplateORM).where(
            DelfTestTemplateORM.class_level == class_level,
            DelfTestTemplateORM.is_active.is_(True),
        )
        rows = self._session.scalars(stmt).all()
        now = datetime.now(timezone.utc)
        for row in rows:
            if exclude_id is not None and row.id == exclude_id:
                continue
            row.is_active = False
            row.updated_at = now


def _session_to_domain(row: DelfTestSessionORM) -> DelfTestSession:
    return DelfTestSession(
        id=row.id,
        user_id=row.user_id,
        class_level=row.class_level,
        target_delf_level=row.target_delf_level,
        status=row.status,
        question_ids_by_category=dict(row.question_ids_by_category or {}),
        answers=list(row.answers or []),
        category_scores={k: int(v) for k, v in (row.category_scores or {}).items()},
        overall_score=row.overall_score,
        achieved_delf_level=row.achieved_delf_level,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
    )


def _config_to_domain(row: DelfTestConfigORM) -> DelfTestConfig:
    return DelfTestConfig(
        id=row.id,
        questions_per_category=row.questions_per_category,
        level_thresholds=list(row.level_thresholds or []),
        updated_at=row.updated_at,
    )


def _template_to_domain(row: DelfTestTemplateORM) -> DelfTestTemplate:
    return DelfTestTemplate(
        id=row.id,
        name=row.name,
        description=row.description,
        class_level=row.class_level,
        target_delf_level=row.target_delf_level,
        is_active=row.is_active,
        question_ids_by_category={
            str(k): [str(qid) for qid in v]
            for k, v in (row.question_ids_by_category or {}).items()
        },
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _default_config() -> DelfTestConfig:
    now = datetime.now(timezone.utc)
    return DelfTestConfig(
        id=uuid.UUID(int=0),
        questions_per_category=DEFAULT_QUESTIONS_PER_CATEGORY,
        level_thresholds=list(DEFAULT_DELF_LEVEL_THRESHOLDS),
        updated_at=now,
    )
