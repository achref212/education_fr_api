from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class GameParticipantORM(Base):
    __tablename__ = "game_participants"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_game_participants"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    session: Mapped[GameSessionORM] = relationship(  # type: ignore[name-defined]
        "GameSessionORM", back_populates="participants"
    )
    user: Mapped[UserORM] = relationship("UserORM", back_populates="game_participations")  # type: ignore[name-defined]
