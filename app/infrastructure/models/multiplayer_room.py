from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class MultiplayerRoomORM(Base):
    """Server-side snapshot of multiplayer rooms (optional sync from clients)."""

    __tablename__ = "multiplayer_rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    professor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    class_level: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    active_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    sessions: Mapped[list[GameSessionORM]] = relationship(  # type: ignore[name-defined]
        "GameSessionORM",
        back_populates="room",
        foreign_keys="GameSessionORM.room_id",
    )
