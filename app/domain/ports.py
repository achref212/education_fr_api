from datetime import date
from typing import Any, Protocol
from uuid import UUID

from app.domain.entities import (
    ContactMessage,
    Lesson,
    MultiplayerRoom,
    ProgressData,
    QuizQuestion,
    Recommendation,
    School,
    SchoolWithHash,
    Story,
    User,
    UserProgressRow,
    UserWithHash,
)


class IUserRepository(Protocol):
    def create_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        level: str,
        is_active: bool = False,
        phone: str | None = None,
        date_of_birth: date | None = None,
        class_level: str | None = None,
        school_id: str | None = None,
    ) -> User: ...

    def change_password(self, user_id: UUID, password_hash: str) -> None: ...

    def get_by_email(self, email: str) -> UserWithHash | None: ...

    def get_by_id(self, user_id: UUID) -> User | None: ...

    def update_password(self, user_id: UUID, password_hash: str) -> None: ...

    def activate_user(self, user_id: UUID) -> None: ...


class IEmailSender(Protocol):
    def send_password_reset_code(
        self,
        to_email: str,
        to_name: str,
        code: str,
        expires_minutes: int,
    ) -> None: ...

    def send_activation_code(
        self,
        to_email: str,
        to_name: str,
        code: str,
        expires_minutes: int,
    ) -> None: ...

    def send_school_welcome(
        self,
        to_email: str,
        school_name: str,
        plain_password: str,
        dashboard_url: str,
    ) -> None: ...

    def send_prof_welcome(
        self,
        to_email: str,
        prof_name: str,
        plain_password: str,
        dashboard_url: str,
    ) -> None: ...


class IProgressRepository(Protocol):
    def get_for_user(self, user_id: UUID) -> ProgressData: ...

    def upsert_for_user(self, user_id: UUID, data: ProgressData) -> None: ...


class IAdminUserRepository(Protocol):
    def create_user_with_role(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        level: str,
        role: str,
        teacher_school_id: UUID | None = None,
        class_level: str | None = None,
        phone: str | None = None,
        date_of_birth: date | None = None,
        must_change_password: bool = False,
    ) -> User: ...

    def list_users(self) -> list[User]: ...

    def count_users(self) -> int: ...

    def count_active_users(self) -> int: ...

    def count_by_level(self) -> dict[str, int]: ...

    def count_admins(self) -> int: ...

    def update_user(
        self,
        user_id: UUID,
        *,
        role: str | None = None,
        level: str | None = None,
        is_active: bool | None = None,
        school_id: UUID | None = None,
        class_level: str | None = None,
        phone: str | None = None,
        date_of_birth: date | None = None,
    ) -> User | None: ...

    def delete_user(self, user_id: UUID) -> bool: ...


class ISchoolRepository(Protocol):
    def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        created_by_admin_id: UUID,
        address: str | None,
        city: str | None,
        postal_code: str | None,
        phone: str | None,
        director_name: str | None,
        must_change_password: bool = False,
    ) -> School: ...

    def change_password(self, school_id: UUID, password_hash: str) -> None: ...

    def get_by_id(self, school_id: UUID) -> School | None: ...

    def get_by_email(self, email: str) -> SchoolWithHash | None: ...

    def list_all(self) -> list[School]: ...

    def update(
        self,
        school_id: UUID,
        *,
        name: str | None = None,
        address: str | None = None,
        city: str | None = None,
        postal_code: str | None = None,
        phone: str | None = None,
        director_name: str | None = None,
        is_active: bool | None = None,
    ) -> School | None: ...

    def delete(self, school_id: UUID) -> bool: ...

    def list_students(self, school_id: UUID) -> list[User]: ...

    def list_professors(self, school_id: UUID) -> list[User]: ...

    def count(self) -> int: ...


class IRecommendationRepository(Protocol):
    def create(
        self,
        student_id: UUID,
        professor_id: UUID,
        content: str,
    ) -> Recommendation: ...

    def list_for_student(self, student_id: UUID) -> list[Recommendation]: ...


class ILessonRepository(Protocol):
    def list_all(self) -> list[Lesson]: ...

    def list_by_level(self, level: str) -> list[Lesson]: ...

    def list_by_category(self, category: str) -> list[Lesson]: ...

    def get(self, lesson_id: UUID) -> Lesson | None: ...

    def create(
        self,
        title: str,
        content: str,
        category: str,
        level: str,
        sort_order: int,
    ) -> Lesson: ...

    def update(
        self,
        lesson_id: UUID,
        *,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        level: str | None = None,
        sort_order: int | None = None,
    ) -> Lesson | None: ...

    def delete(self, lesson_id: UUID) -> bool: ...

    def count(self) -> int: ...

    def count_by_category(self) -> dict[str, int]: ...


class IQuizRepository(Protocol):
    def list_all(self) -> list[QuizQuestion]: ...

    def list_by_level(self, level: str) -> list[QuizQuestion]: ...

    def get(self, question_id: UUID) -> QuizQuestion | None: ...

    def create(
        self,
        question: str,
        options: list[Any],
        correct_index: int,
        explanation: str | None,
        category: str,
        level: str,
    ) -> QuizQuestion: ...

    def update(
        self,
        question_id: UUID,
        *,
        question: str | None = None,
        options: list[Any] | None = None,
        correct_index: int | None = None,
        explanation: str | None = None,
        category: str | None = None,
        level: str | None = None,
    ) -> QuizQuestion | None: ...

    def delete(self, question_id: UUID) -> bool: ...

    def count(self) -> int: ...


class IStoryRepository(Protocol):
    def list_all(self) -> list[Story]: ...

    def list_by_level(self, level: str) -> list[Story]: ...

    def get(self, story_id: UUID) -> Story | None: ...

    def create(
        self,
        title: str,
        content: str,
        level: str,
        audio_url: str | None,
    ) -> Story: ...

    def update(
        self,
        story_id: UUID,
        *,
        title: str | None = None,
        content: str | None = None,
        level: str | None = None,
        audio_url: str | None = None,
    ) -> Story | None: ...

    def delete(self, story_id: UUID) -> bool: ...

    def count(self) -> int: ...


class IContactRepository(Protocol):
    def list_all(self) -> list[ContactMessage]: ...

    def get(self, message_id: UUID) -> ContactMessage | None: ...

    def mark_read(self, message_id: UUID, read: bool = True) -> ContactMessage | None: ...

    def delete(self, message_id: UUID) -> bool: ...

    def count_unread(self) -> int: ...


class IAdminProgressRepository(Protocol):
    def list_all_with_users(self) -> list[UserProgressRow]: ...


class IMultiplayerRepository(Protocol):
    def list_all(self) -> list[MultiplayerRoom]: ...

    def list_by_professor(self, professor_id: UUID) -> list[MultiplayerRoom]: ...

    def create(
        self,
        room_code: str,
        label: str | None,
        professor_id: UUID,
        school_id: UUID | None,
    ) -> MultiplayerRoom: ...

    def count(self) -> int: ...
