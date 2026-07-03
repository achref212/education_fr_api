from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID


@dataclass
class User:
    id: UUID
    email: str
    first_name: str
    last_name: str
    level: str
    created_at: datetime
    role: str = "user"
    is_active: bool = True
    must_change_password: bool = False
    class_level: str | None = None
    school_id: UUID | None = None
    teacher_school_id: UUID | None = None
    phone: str | None = None
    date_of_birth: date | None = None


@dataclass
class UserWithHash:
    user: User
    password_hash: str


@dataclass
class School:
    id: UUID
    name: str
    email: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    director_name: str | None = None
    created_by_admin_id: UUID | None = None


@dataclass
class SchoolWithHash:
    school: School
    password_hash: str


@dataclass
class Recommendation:
    id: UUID
    student_id: UUID
    content: str
    created_at: datetime
    professor_id: UUID | None = None


@dataclass
class ProgressData:
    lessons_completed: list[str]
    quiz_scores: dict[str, list[int]]
    exercise_scores: dict[str, list[int]]

    @classmethod
    def empty(cls) -> "ProgressData":
        return cls(lessons_completed=[], quiz_scores={}, exercise_scores={})

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProgressData":
        qc = d.get("quizScores") or {}
        ec = d.get("exerciseScores") or {}
        return cls(
            lessons_completed=list(d.get("lessonsCompleted") or []),
            quiz_scores={k: list(v) for k, v in qc.items()},
            exercise_scores={k: list(v) for k, v in ec.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "lessonsCompleted": self.lessons_completed,
            "quizScores": self.quiz_scores,
            "exerciseScores": self.exercise_scores,
        }


@dataclass
class Lesson:
    id: UUID
    title: str
    content: str
    category: str
    level: str
    sort_order: int
    created_at: datetime


@dataclass
class QuizQuestion:
    id: UUID
    question: str
    options: list[Any]
    correct_index: int
    explanation: str | None
    category: str
    level: str


@dataclass
class Story:
    id: UUID
    title: str
    content: str
    level: str
    audio_url: str | None
    created_at: datetime


@dataclass
class ContactMessage:
    id: UUID
    name: str
    email: str
    subject: str
    message: str
    created_at: datetime
    read: bool


@dataclass
class MultiplayerRoom:
    id: UUID
    room_code: str
    data: dict[str, Any]
    label: str | None
    created_at: datetime
    updated_at: datetime
    professor_id: UUID | None = None
    school_id: UUID | None = None


@dataclass
class UserProgressRow:
    user: User
    progress: ProgressData
