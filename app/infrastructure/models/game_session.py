from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class GameSessionORM(Base):
    __tablename__ = "game_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("multiplayer_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    class_level: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="waiting")
    question_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    room: Mapped[MultiplayerRoomORM] = relationship(  # type: ignore[name-defined]
        "MultiplayerRoomORM",
        back_populates="sessions",
        foreign_keys=[room_id],
    )
    game: Mapped[GameORM] = relationship("GameORM", back_populates="sessions")  # type: ignore[name-defined]
    participants: Mapped[list[GameParticipantORM]] = relationship(  # type: ignore[name-defined]
        "GameParticipantORM", back_populates="session"
    )
