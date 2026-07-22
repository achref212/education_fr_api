from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(128), nullable=False)
    class_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="user", server_default="user"
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    teacher_school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_learning_path_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    progress: Mapped[UserProgressORM | None] = relationship(  # type: ignore[name-defined]
        "UserProgressORM", back_populates="user", uselist=False
    )
    school: Mapped[SchoolORM | None] = relationship(  # type: ignore[name-defined]
        "SchoolORM",
        foreign_keys=[school_id],
        back_populates="students",
    )
    teacher_school: Mapped[SchoolORM | None] = relationship(  # type: ignore[name-defined]
        "SchoolORM",
        foreign_keys=[teacher_school_id],
        back_populates="professors",
    )
    received_recommendations: Mapped[list[RecommendationORM]] = relationship(  # type: ignore[name-defined]
        "RecommendationORM",
        foreign_keys="[RecommendationORM.student_id]",
        back_populates="student",
    )
    step_progress: Mapped[list[StudentStepProgressORM]] = relationship(  # type: ignore[name-defined]
        "StudentStepProgressORM",
        back_populates="user",
    )
    stats: Mapped[StudentStatsORM | None] = relationship(  # type: ignore[name-defined]
        "StudentStatsORM",
        back_populates="user",
        uselist=False,
    )
    game_participations: Mapped[list[GameParticipantORM]] = relationship(  # type: ignore[name-defined]
        "GameParticipantORM",
        back_populates="user",
    )
    assigned_learning_path: Mapped[LearningPathORM | None] = relationship(  # type: ignore[name-defined]
        "LearningPathORM",
        foreign_keys=[assigned_learning_path_id],
    )
