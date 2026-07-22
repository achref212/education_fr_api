from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class DelfMockExamORM(Base):
    __tablename__ = "delf_mock_exams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    track: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    total_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sections: Mapped[list[DelfMockSectionORM]] = relationship(  # type: ignore[name-defined]
        "DelfMockSectionORM",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="DelfMockSectionORM.section_order",
    )
    assets: Mapped[list[DelfMockAssetORM]] = relationship(  # type: ignore[name-defined]
        "DelfMockAssetORM",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="DelfMockAssetORM.created_at",
    )


class DelfMockSectionORM(Base):
    __tablename__ = "delf_mock_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delf_mock_exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    section_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    exam: Mapped[DelfMockExamORM] = relationship("DelfMockExamORM", back_populates="sections")  # type: ignore[name-defined]
    items: Mapped[list[DelfMockItemORM]] = relationship(  # type: ignore[name-defined]
        "DelfMockItemORM",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="DelfMockItemORM.item_order",
    )


class DelfMockItemORM(Base):
    __tablename__ = "delf_mock_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delf_mock_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    answer_key: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rubric: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    section: Mapped[DelfMockSectionORM] = relationship("DelfMockSectionORM", back_populates="items")  # type: ignore[name-defined]


class DelfMockAssetORM(Base):
    __tablename__ = "delf_mock_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delf_mock_exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    exam: Mapped[DelfMockExamORM] = relationship("DelfMockExamORM", back_populates="assets")  # type: ignore[name-defined]
