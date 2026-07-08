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
    professor_id: UUID | None = None


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
    class_level: str | None = None
    active_session_id: UUID | None = None


@dataclass
class LearningPath:
    id: UUID
    class_level: str
    title: str
    delf_target_level: str
    created_at: datetime
    description: str | None = None
    is_active: bool = True


@dataclass
class LearningPathStep:
    id: UUID
    path_id: UUID
    step_order: int
    step_type: str
    title: str
    xp_reward: int
    created_at: datetime
    quiz_category: str | None = None
    lesson_id: UUID | None = None
    story_id: UUID | None = None
    required_step_id: UUID | None = None


@dataclass
class StudentStepProgress:
    id: UUID
    user_id: UUID
    step_id: UUID
    status: str
    attempts: int
    updated_at: datetime
    score: int | None = None
    completed_at: datetime | None = None


@dataclass
class StudentStats:
    user_id: UUID
    total_xp: int
    current_streak: int
    longest_streak: int
    preferred_difficulty: str
    updated_at: datetime
    last_activity_date: date | None = None


@dataclass
class Game:
    id: UUID
    slug: str
    name: str
    min_players: int
    max_players: int
    default_question_count: int
    created_at: datetime
    description: str | None = None
    is_active: bool = True


@dataclass
class GameSession:
    id: UUID
    room_id: UUID
    game_id: UUID
    difficulty: str
    class_level: str
    status: str
    question_ids: list[str]
    current_round: int
    total_rounds: int
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass
class GameParticipant:
    id: UUID
    session_id: UUID
    user_id: UUID
    score: int
    answers: list[dict[str, Any]]
    joined_at: datetime
    rank: int | None = None
    finished_at: datetime | None = None


@dataclass
class ParcoursSummary:
    class_level: str
    delf_target_level: str
    completion_percent: float
    total_steps: int
    completed_steps: int
    total_xp: int
    current_streak: int
    preferred_difficulty: str
    next_step_id: UUID | None = None
    next_step_title: str | None = None


@dataclass
class UserProgressRow:
    user: User
    progress: ProgressData


@dataclass
class DelfTestSession:
    id: UUID
    user_id: UUID
    class_level: str
    target_delf_level: str
    status: str
    question_ids_by_category: dict[str, list[str]]
    answers: list[dict[str, Any]]
    category_scores: dict[str, int]
    created_at: datetime
    overall_score: int | None = None
    achieved_delf_level: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass
class DelfTestConfig:
    id: UUID
    questions_per_category: int
    level_thresholds: list[dict[str, int | str]]
    updated_at: datetime
