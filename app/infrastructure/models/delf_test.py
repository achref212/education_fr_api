from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class DelfTestSessionORM(Base):
    __tablename__ = "delf_test_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    class_level: Mapped[str] = mapped_column(String(32), nullable=False)
    target_delf_level: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    question_ids_by_category: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    answers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    category_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    achieved_delf_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DelfTestConfigORM(Base):
    __tablename__ = "delf_test_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    questions_per_category: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    level_thresholds: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DelfTestTemplateORM(Base):
    __tablename__ = "delf_test_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    class_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_delf_level: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    question_ids_by_category: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
