from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from app.domain.entities import (
    ContactMessage,
    DelfMockExam,
    DelfMockAttempt,
    DelfTestConfig,
    DelfTestSession,
    DelfTestTemplate,
    Game,
    GameParticipant,
    GameSession,
    LearningPath,
    LearningPathStep,
    Lesson,
    MediaAsset,
    MultiplayerRoom,
    ProgressData,
    QuizQuestion,
    Recommendation,
    School,
    SchoolWithHash,
    Story,
    StudentStats,
    StudentLeaderboardEntry,
    StudentReviewItem,
    StudentStepProgress,
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

    def update_profile(
        self,
        user_id: UUID,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        date_of_birth: date | None = None,
        profile_picture_url: str | None = None,
        clear_profile_picture_url: bool = False,
    ) -> User | None: ...

    def assign_learning_path(
        self, user_id: UUID, learning_path_id: UUID | None
    ) -> User | None: ...


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
        profile_picture_url: str | None = None,
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
        assigned_learning_path_id: UUID | None = None,
        profile_picture_url: str | None = None,
        clear_profile_picture_url: bool = False,
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
        logo_url: str | None = None,
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
        logo_url: str | None = None,
        clear_logo_url: bool = False,
    ) -> School | None: ...

    def delete(self, school_id: UUID) -> bool: ...

    def list_students(self, school_id: UUID) -> list[User]: ...

    def list_professors(self, school_id: UUID) -> list[User]: ...

    def count(self) -> int: ...


class IMediaAssetRepository(Protocol):
    def create(
        self,
        *,
        owner_type: str | None,
        owner_id: UUID | None,
        asset_type: str,
        title: str | None,
        url: str,
        storage_path: str | None,
        mime_type: str | None,
        size_bytes: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> MediaAsset: ...

    def list_all(
        self,
        *,
        owner_type: str | None = None,
        owner_id: UUID | None = None,
        asset_type: str | None = None,
        is_active: bool | None = True,
    ) -> list[MediaAsset]: ...

    def archive(self, asset_id: UUID) -> MediaAsset | None: ...


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

    def list_by_professor(self, professor_id: UUID) -> list[Lesson]: ...

    def list_visible_for_user(self, user: User) -> list[Lesson]: ...

    def list_by_level(self, level: str) -> list[Lesson]: ...

    def list_by_category(
        self, category: str, user: User | None = None
    ) -> list[Lesson]: ...

    def get(self, lesson_id: UUID) -> Lesson | None: ...

    def create(
        self,
        title: str,
        content: str,
        category: str,
        level: str,
        sort_order: int,
        professor_id: UUID | None = None,
        school_id: UUID | None = None,
        visibility: str = "public",
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
        school_id: UUID | None = None,
        visibility: str | None = None,
    ) -> Lesson | None: ...

    def delete(self, lesson_id: UUID) -> bool: ...

    def count(self) -> int: ...

    def count_by_category(self) -> dict[str, int]: ...


class IQuizRepository(Protocol):
    def list_all(self) -> list[QuizQuestion]: ...

    def list_by_professor(self, professor_id: UUID) -> list[QuizQuestion]: ...

    def list_visible_for_user(self, user: User) -> list[QuizQuestion]: ...

    def list_by_level(self, level: str) -> list[QuizQuestion]: ...

    def list_by_level_and_category(
        self, level: str, category: str
    ) -> list[QuizQuestion]: ...

    def get(self, question_id: UUID) -> QuizQuestion | None: ...

    def create(
        self,
        question: str,
        options: list[Any],
        correct_index: int,
        explanation: str | None,
        category: str,
        level: str,
        professor_id: UUID | None = None,
        school_id: UUID | None = None,
        visibility: str = "public",
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
        visibility: str | None = None,
    ) -> QuizQuestion | None: ...

    def delete(self, question_id: UUID) -> bool: ...

    def count(self) -> int: ...


class IStoryRepository(Protocol):
    def list_all(self) -> list[Story]: ...

    def list_by_professor(self, professor_id: UUID) -> list[Story]: ...

    def list_visible_for_user(self, user: User) -> list[Story]: ...

    def list_by_level(self, level: str) -> list[Story]: ...

    def get(self, story_id: UUID) -> Story | None: ...

    def create(
        self,
        title: str,
        content: str,
        level: str,
        audio_url: str | None,
        professor_id: UUID | None = None,
        school_id: UUID | None = None,
        visibility: str = "public",
    ) -> Story: ...

    def update(
        self,
        story_id: UUID,
        *,
        title: str | None = None,
        content: str | None = None,
        level: str | None = None,
        audio_url: str | None = None,
        visibility: str | None = None,
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

    def get_by_id(self, room_id: UUID) -> MultiplayerRoom | None: ...

    def get_by_code(self, room_code: str) -> MultiplayerRoom | None: ...

    def list_for_student(self, student_id: UUID) -> list[MultiplayerRoom]: ...

    def create(
        self,
        room_code: str,
        label: str | None,
        professor_id: UUID,
        school_id: UUID | None,
        data: dict | None = None,
        class_level: str | None = None,
    ) -> MultiplayerRoom: ...

    def update_data(self, room_id: UUID, data: dict[str, Any]) -> MultiplayerRoom | None: ...

    def set_active_session(
        self, room_id: UUID, session_id: UUID | None
    ) -> MultiplayerRoom | None: ...

    def count(self) -> int: ...


class ILearningPathRepository(Protocol):
    def get_by_class_level(self, class_level: str) -> LearningPath | None: ...

    def get_default_for_class_level(self, class_level: str) -> LearningPath | None: ...

    def find_match(
        self, class_level: str, delf_level: str | None, score: int | None
    ) -> LearningPath | None: ...

    def get(self, path_id: UUID) -> LearningPath | None: ...

    def list_all(self) -> list[LearningPath]: ...

    def count_steps(self, path_id: UUID) -> int: ...

    def count_assigned_users(self, path_id: UUID) -> int: ...

    def list_steps(self, path_id: UUID) -> list[LearningPathStep]: ...

    def get_step(self, step_id: UUID) -> LearningPathStep | None: ...

    def create_path(
        self,
        class_level: str,
        title: str,
        delf_target_level: str,
        description: str | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        is_default: bool = False,
    ) -> LearningPath: ...

    def update_path(
        self,
        path_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        delf_target_level: str | None = None,
        is_active: bool | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        is_default: bool | None = None,
    ) -> LearningPath | None: ...

    def delete_path(self, path_id: UUID) -> bool: ...

    def create_step(
        self,
        path_id: UUID,
        step_order: int,
        step_type: str,
        title: str,
        xp_reward: int,
        quiz_category: str | None = None,
        lesson_id: UUID | None = None,
        story_id: UUID | None = None,
        required_step_id: UUID | None = None,
    ) -> LearningPathStep: ...

    def update_step(
        self,
        step_id: UUID,
        *,
        step_order: int | None = None,
        step_type: str | None = None,
        title: str | None = None,
        xp_reward: int | None = None,
        quiz_category: str | None = None,
        lesson_id: UUID | None = None,
        story_id: UUID | None = None,
        required_step_id: UUID | None = None,
    ) -> LearningPathStep | None: ...

    def delete_step(self, step_id: UUID) -> bool: ...


class IStudentProgressRepository(Protocol):
    def get_stats(self, user_id: UUID) -> StudentStats | None: ...

    def upsert_stats(self, stats: StudentStats) -> StudentStats: ...

    def get_step_progress(
        self, user_id: UUID, step_id: UUID
    ) -> StudentStepProgress | None: ...

    def list_step_progress(self, user_id: UUID) -> list[StudentStepProgress]: ...

    def upsert_step_progress(
        self, progress: StudentStepProgress
    ) -> StudentStepProgress: ...

    def list_leaderboard(
        self,
        *,
        school_id: UUID | None = None,
        class_level: str | None = None,
    ) -> list[StudentLeaderboardEntry]: ...


class IStudentReviewRepository(Protocol):
    def upsert_wrong_answer(
        self,
        *,
        user_id: UUID,
        source_type: str,
        source_id: str | None,
        question_id: str | None,
        category: str,
        question: str,
        options: list[Any],
        selected_index: int | None,
        correct_index: int | None,
        explanation: str | None,
    ) -> StudentReviewItem: ...

    def list_for_user(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> list[StudentReviewItem]: ...

    def get_for_user(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> StudentReviewItem | None: ...

    def mark_completed(
        self,
        user_id: UUID,
        item_id: UUID,
    ) -> StudentReviewItem | None: ...


class IGameRepository(Protocol):
    def list_games(self, active_only: bool = True) -> list[Game]: ...

    def get_game_by_slug(self, slug: str) -> Game | None: ...

    def get_game(self, game_id: UUID) -> Game | None: ...

    def create_game(
        self,
        slug: str,
        name: str,
        min_players: int,
        max_players: int,
        default_question_count: int,
        description: str | None = None,
    ) -> Game: ...

    def update_game(
        self,
        game_id: UUID,
        *,
        name: str | None = None,
        min_players: int | None = None,
        max_players: int | None = None,
        default_question_count: int | None = None,
        description: str | None = None,
    ) -> Game | None: ...

    def create_session(
        self,
        room_id: UUID,
        game_id: UUID,
        difficulty: str,
        class_level: str,
        question_ids: list[str],
        total_rounds: int,
        settings: dict[str, Any],
    ) -> GameSession: ...

    def get_session(self, session_id: UUID) -> GameSession | None: ...

    def update_session(
        self,
        session_id: UUID,
        *,
        status: str | None = None,
        current_round: int | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> GameSession | None: ...

    def list_participants(self, session_id: UUID) -> list[GameParticipant]: ...

    def get_participant(
        self, session_id: UUID, user_id: UUID
    ) -> GameParticipant | None: ...

    def add_participant(
        self, session_id: UUID, user_id: UUID
    ) -> GameParticipant: ...

    def update_participant(
        self,
        participant_id: UUID,
        *,
        score: int | None = None,
        rank: int | None = None,
        answers: list[dict[str, Any]] | None = None,
        finished_at: datetime | None = None,
    ) -> GameParticipant | None: ...


class IDelfTestRepository(Protocol):
    def create_session(
        self,
        user_id: UUID,
        class_level: str,
        target_delf_level: str,
        question_ids_by_category: dict[str, list[str]],
    ) -> DelfTestSession: ...

    def get_session(self, session_id: UUID) -> DelfTestSession | None: ...

    def get_active_session(self, user_id: UUID) -> DelfTestSession | None: ...

    def update_session(
        self,
        session_id: UUID,
        *,
        status: str | None = None,
        answers: list[dict[str, Any]] | None = None,
        category_scores: dict[str, int] | None = None,
        overall_score: int | None = None,
        achieved_delf_level: str | None = None,
        finished_at: datetime | None = None,
    ) -> DelfTestSession | None: ...

    def list_sessions_for_user(self, user_id: UUID) -> list[DelfTestSession]: ...

    def list_all_sessions(
        self,
        *,
        user_id: UUID | None = None,
        class_level: str | None = None,
        status: str | None = None,
    ) -> list[DelfTestSession]: ...

    def get_config(self) -> DelfTestConfig: ...

    def update_config(
        self,
        *,
        questions_per_category: int | None = None,
        level_thresholds: list[dict[str, int | str]] | None = None,
    ) -> DelfTestConfig: ...

    def list_templates(self) -> list[DelfTestTemplate]: ...

    def get_template(self, template_id: UUID) -> DelfTestTemplate | None: ...

    def get_active_template_for_class(self, class_level: str) -> DelfTestTemplate | None: ...

    def create_template(
        self,
        *,
        name: str,
        description: str | None,
        class_level: str,
        target_delf_level: str,
        is_active: bool,
        question_ids_by_category: dict[str, list[str]],
    ) -> DelfTestTemplate: ...

    def update_template(
        self,
        template_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        class_level: str | None = None,
        target_delf_level: str | None = None,
        is_active: bool | None = None,
        question_ids_by_category: dict[str, list[str]] | None = None,
    ) -> DelfTestTemplate | None: ...


class IDelfMockExamRepository(Protocol):
    def list_exams(
        self,
        *,
        track: str | None = None,
        level: str | None = None,
        status: str | None = None,
    ) -> list[DelfMockExam]: ...

    def get_exam(self, exam_id: UUID) -> DelfMockExam | None: ...

    def create_exam(
        self,
        *,
        track: str,
        level: str,
        title: str,
        description: str | None,
        status: str,
        total_duration_minutes: int,
        total_points: int,
        source_notes: str | None,
        sections: list[dict[str, Any]],
        assets: list[dict[str, Any]] | None = None,
    ) -> DelfMockExam: ...

    def update_exam(
        self,
        exam_id: UUID,
        *,
        track: str,
        level: str,
        title: str,
        description: str | None,
        status: str,
        total_duration_minutes: int,
        total_points: int,
        source_notes: str | None,
        sections: list[dict[str, Any]],
        assets: list[dict[str, Any]] | None = None,
    ) -> DelfMockExam | None: ...

    def archive_exam(self, exam_id: UUID) -> DelfMockExam | None: ...


class IDelfMockAttemptRepository(Protocol):
    def create_attempt(
        self,
        *,
        user_id: UUID,
        exam_id: UUID,
    ) -> DelfMockAttempt: ...

    def get_attempt(self, attempt_id: UUID) -> DelfMockAttempt | None: ...

    def get_active_attempt(
        self,
        *,
        user_id: UUID,
        exam_id: UUID,
    ) -> DelfMockAttempt | None: ...

    def update_attempt(
        self,
        attempt_id: UUID,
        *,
        status: str | None = None,
        answers: list[dict[str, Any]] | None = None,
        section_scores: dict[str, int] | None = None,
        overall_score: int | None = None,
        approximate: bool | None = None,
        finished_at: datetime | None = None,
    ) -> DelfMockAttempt | None: ...
