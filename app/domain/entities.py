from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class PasswordResetCode:
    id: UUID
    user_id: UUID
    code_hash: str
    expires_at: datetime
    used: bool
    attempts: int
    created_at: datetime


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


@dataclass
class UserWithHash:
    user: User
    password_hash: str


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


@dataclass
class UserProgressRow:
    user: User
    progress: ProgressData
