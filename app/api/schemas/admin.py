from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities import (
    ContactMessage,
    Lesson,
    MultiplayerRoom,
    QuizQuestion,
    Story,
    User,
    UserProgressRow,
)


# --- Stats ---


class AdminStatsOut(BaseModel):
    totalUsers: int
    activeUsers: int
    totalLessons: int
    totalQuizQuestions: int
    totalStories: int
    unreadMessages: int
    multiplayerRooms: int
    totalSchools: int = 0
    usersByLevel: dict[str, int] = Field(default_factory=dict)
    lessonsByCategory: dict[str, int] = Field(default_factory=dict)


# --- Users ---


class AdminUserOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    email: str
    firstName: str
    lastName: str
    level: str
    createdAt: datetime
    role: str
    isActive: bool

    classLevel: str | None = None
    schoolId: UUID | None = None
    teacherSchoolId: UUID | None = None
    phone: str | None = None
    dateOfBirth: date | None = None
    assignedLearningPathId: UUID | None = None

    @classmethod
    def from_domain(cls, u: User) -> "AdminUserOut":
        return cls(
            id=u.id,
            email=u.email,
            firstName=u.first_name,
            lastName=u.last_name,
            level=u.level,
            createdAt=u.created_at,
            role=u.role,
            isActive=u.is_active,
            classLevel=u.class_level,
            schoolId=u.school_id,
            teacherSchoolId=u.teacher_school_id,
            phone=u.phone,
            dateOfBirth=u.date_of_birth,
            assignedLearningPathId=u.assigned_learning_path_id,
        )


class AdminUserUpdateIn(BaseModel):
    role: str | None = None
    level: str | None = None
    isActive: bool | None = Field(None, alias="isActive")
    classLevel: str | None = None
    phone: str | None = None
    dateOfBirth: date | None = None

    model_config = ConfigDict(populate_by_name=True)


class AdminUserCreateIn(BaseModel):
    email: str
    password: str = Field(min_length=6)
    firstName: str
    lastName: str
    level: str
    role: str = "user"
    phone: str | None = None
    dateOfBirth: date | None = None
    classLevel: str | None = None

    model_config = ConfigDict(populate_by_name=True)


# --- Lessons ---


class LessonOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    title: str
    content: str
    category: str
    level: str
    sortOrder: int
    createdAt: datetime

    @classmethod
    def from_domain(cls, x: Lesson) -> "LessonOut":
        return cls(
            id=x.id,
            title=x.title,
            content=x.content,
            category=x.category,
            level=x.level,
            sortOrder=x.sort_order,
            createdAt=x.created_at,
        )


class LessonCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    content: str
    category: str
    level: str
    sortOrder: int = 0


class LessonUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    content: str | None = None
    category: str | None = None
    level: str | None = None
    sortOrder: int | None = None


# --- Quiz ---


class QuizQuestionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    question: str
    options: list[Any]
    correctIndex: int
    explanation: str | None
    category: str
    level: str

    @classmethod
    def from_domain(cls, x: QuizQuestion) -> "QuizQuestionOut":
        return cls(
            id=x.id,
            question=x.question,
            options=x.options,
            correctIndex=x.correct_index,
            explanation=x.explanation,
            category=x.category,
            level=x.level,
        )


class QuizQuestionCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str
    options: list[Any]
    correctIndex: int
    explanation: str | None = None
    category: str
    level: str


class QuizQuestionUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str | None = None
    options: list[Any] | None = None
    correctIndex: int | None = None
    explanation: str | None = None
    category: str | None = None
    level: str | None = None


# --- Stories ---


class StoryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    title: str
    content: str
    level: str
    audioUrl: str | None
    createdAt: datetime

    @classmethod
    def from_domain(cls, x: Story) -> "StoryOut":
        return cls(
            id=x.id,
            title=x.title,
            content=x.content,
            level=x.level,
            audioUrl=x.audio_url,
            createdAt=x.created_at,
        )


class StoryCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    content: str
    level: str
    audioUrl: str | None = None


class StoryUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    content: str | None = None
    level: str | None = None
    audioUrl: str | None = None


# --- Contact ---


class ContactMessageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    email: str
    subject: str
    message: str
    createdAt: datetime
    read: bool

    @classmethod
    def from_domain(cls, x: ContactMessage) -> "ContactMessageOut":
        return cls(
            id=x.id,
            name=x.name,
            email=x.email,
            subject=x.subject,
            message=x.message,
            createdAt=x.created_at,
            read=x.read,
        )


# --- Progress ---


class UserProgressItemOut(BaseModel):
    user: "AdminUserOut"
    progress: dict[str, Any]

    @classmethod
    def from_row(cls, row: UserProgressRow) -> "UserProgressItemOut":
        return cls(
            user=AdminUserOut.from_domain(row.user),
            progress=row.progress.to_dict(),
        )


# --- Multiplayer ---


class MultiplayerRoomOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    roomCode: str
    data: dict[str, Any]
    label: str | None
    createdAt: datetime
    updatedAt: datetime
    professorId: UUID | None = None
    schoolId: UUID | None = None
    classLevel: str | None = None
    activeSessionId: UUID | None = None
    participantCount: int = 0

    @classmethod
    def from_domain(cls, x: MultiplayerRoom) -> "MultiplayerRoomOut":
        class_level = x.class_level or (x.data.get("classLevel") if x.data else None)
        participants = x.data.get("participants") if x.data else None
        participant_count = len(participants) if isinstance(participants, list) else 0
        return cls(
            id=x.id,
            roomCode=x.room_code,
            data=x.data,
            label=x.label,
            createdAt=x.created_at,
            updatedAt=x.updated_at,
            professorId=x.professor_id,
            schoolId=x.school_id,
            classLevel=str(class_level) if class_level else None,
            activeSessionId=x.active_session_id,
            participantCount=participant_count,
        )


# --- Setup ---


class SetupStatusOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    setupComplete: bool


class AdminSetupIn(BaseModel):
    email: str
    password: str = Field(min_length=6)
    firstName: str
    lastName: str
    level: str = "2e"
    phone: str | None = None
    dateOfBirth: date | None = None

    model_config = ConfigDict(populate_by_name=True)
