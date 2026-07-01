from typing import Any, Protocol
from uuid import UUID

from app.domain.entities import (
    ContactMessage,
    Lesson,
    MultiplayerRoom,
    PasswordResetCode,
    ProgressData,
    QuizQuestion,
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
    ) -> User: ...

    def get_by_email(self, email: str) -> UserWithHash | None: ...

    def get_by_id(self, user_id: UUID) -> User | None: ...

    def update_password(self, user_id: UUID, password_hash: str) -> None: ...


class IPasswordResetRepository(Protocol):
    def create(
        self,
        user_id: UUID,
        code_hash: str,
        expires_at: Any,
    ) -> PasswordResetCode: ...

    def get_latest_for_user(self, user_id: UUID) -> PasswordResetCode | None: ...

    def get_by_id(self, code_id: UUID) -> PasswordResetCode | None: ...

    def increment_attempts(self, code_id: UUID) -> None: ...

    def mark_used(self, code_id: UUID) -> None: ...

    def invalidate_all_for_user(self, user_id: UUID) -> None: ...


class IEmailSender(Protocol):
    def send_password_reset_code(
        self,
        to_email: str,
        to_name: str,
        code: str,
        expires_minutes: int,
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
    ) -> User | None: ...

    def delete_user(self, user_id: UUID) -> bool: ...


class ILessonRepository(Protocol):
    def list_all(self) -> list[Lesson]: ...

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

    def count(self) -> int: ...
