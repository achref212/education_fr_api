from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.auth_service import AuthService
from app.application.ai_content_service import AIContentService
from app.application.ai_parcours_assignment_service import AIParcoursAssignmentService
from app.application.avatar_image_service import AvatarImageService
from app.application.delf_mock_exam_service import DelfMockExamService
from app.application.delf_test_service import DelfTestService
from app.application.difficulty_service import DifficultyService
from app.application.game_session_service import GameSessionService
from app.application.media_asset_service import MediaAssetService
from app.application.parcours_service import ParcoursService
from app.application.progress_service import ProgressService
from app.application.student_stats_service import StudentStatsService
from app.application.student_service import StudentService
from app.application.student_delf_mock_exam_service import StudentDelfMockExamService
from app.core.config import get_settings
from app.core.security import decode_token, parse_school_id, parse_user_id
from app.domain.entities import School, User
from app.domain.ports import (
    IAdminProgressRepository,
    IAdminUserRepository,
    IContactRepository,
    IDelfMockExamRepository,
    IDelfMockAttemptRepository,
    IDelfTestRepository,
    IEmailSender,
    IGameRepository,
    ILearningPathRepository,
    ILessonRepository,
    IMultiplayerRepository,
    IMediaAssetRepository,
    IProgressRepository,
    IQuizRepository,
    IRecommendationRepository,
    ISchoolRepository,
    IStoryRepository,
    IStudentProgressRepository,
    IStudentReviewRepository,
    IUserRepository,
)
from app.infrastructure.db.session import get_db
from app.infrastructure.email.smtp_email_sender import (
    ConsoleFallbackEmailSender,
    SmtpEmailSender,
)
from app.infrastructure.repositories.sql_admin_progress_repository import (
    SqlAdminProgressRepository,
)
from app.infrastructure.repositories.sql_admin_user_repository import (
    SqlAdminUserRepository,
)
from app.infrastructure.repositories.sql_contact_repository import SqlContactRepository
from app.infrastructure.repositories.sql_delf_mock_exam_repository import (
    SqlDelfMockExamRepository,
)
from app.infrastructure.repositories.sql_delf_mock_attempt_repository import (
    SqlDelfMockAttemptRepository,
)
from app.infrastructure.repositories.sql_delf_test_repository import SqlDelfTestRepository
from app.infrastructure.repositories.sql_game_repository import SqlGameRepository
from app.infrastructure.repositories.sql_learning_path_repository import (
    SqlLearningPathRepository,
)
from app.infrastructure.repositories.sql_lesson_repository import SqlLessonRepository
from app.infrastructure.repositories.sql_media_asset_repository import (
    SqlMediaAssetRepository,
)
from app.infrastructure.repositories.sql_multiplayer_repository import (
    SqlMultiplayerRepository,
)
from app.infrastructure.repositories.sql_progress_repository import SqlProgressRepository
from app.infrastructure.repositories.sql_quiz_repository import SqlQuizRepository
from app.infrastructure.repositories.sql_recommendation_repository import (
    SqlRecommendationRepository,
)
from app.infrastructure.repositories.sql_school_repository import SqlSchoolRepository
from app.infrastructure.repositories.sql_story_repository import SqlStoryRepository
from app.infrastructure.repositories.sql_student_progress_repository import (
    SqlStudentProgressRepository,
)
from app.infrastructure.repositories.sql_student_review_repository import (
    SqlStudentReviewRepository,
)
from app.infrastructure.repositories.sql_user_repository import SqlUserRepository

security = HTTPBearer(auto_error=False)


def get_user_repo(db: Session = Depends(get_db)) -> IUserRepository:
    return SqlUserRepository(db)


def get_progress_repo(db: Session = Depends(get_db)) -> IProgressRepository:
    return SqlProgressRepository(db)


def get_school_repo(db: Session = Depends(get_db)) -> ISchoolRepository:
    return SqlSchoolRepository(db)


def get_recommendation_repo(db: Session = Depends(get_db)) -> IRecommendationRepository:
    return SqlRecommendationRepository(db)


def get_email_sender() -> IEmailSender:
    settings = get_settings()
    if not settings.smtp_host:
        return ConsoleFallbackEmailSender()
    return SmtpEmailSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_email=settings.smtp_from_email,
        from_name=settings.smtp_from_name,
        dashboard_url=settings.dashboard_url,
        use_ssl=settings.smtp_use_ssl,
        use_tls=settings.smtp_use_tls,
    )


def get_auth_service(
    users: IUserRepository = Depends(get_user_repo),
    email_sender: IEmailSender = Depends(get_email_sender),
    schools: ISchoolRepository = Depends(get_school_repo),
    admin_users: IAdminUserRepository = Depends(
        lambda db=Depends(get_db): SqlAdminUserRepository(db)
    ),
) -> AuthService:
    settings = get_settings()
    return AuthService(
        users=users,
        email_sender=email_sender,
        reset_expire_minutes=settings.password_reset_code_expire_minutes,
        schools=schools,
        admin_users=admin_users,
        dashboard_url=settings.dashboard_url,
    )


def get_progress_service(
    progress: IProgressRepository = Depends(get_progress_repo),
) -> ProgressService:
    return ProgressService(progress)


def get_ai_content_service() -> AIContentService:
    return AIContentService.from_settings(get_settings())


def get_avatar_image_service() -> AvatarImageService:
    return AvatarImageService.from_settings(get_settings())


def get_current_user(
    db: Session = Depends(get_db),
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    if cred is None or not cred.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    sub = decode_token(cred.credentials)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    uid = parse_user_id(sub)
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )
    repo = SqlUserRepository(db)
    user = repo.get_by_id(uid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )
    return user


def get_current_school(
    db: Session = Depends(get_db),
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> School:
    if cred is None or not cred.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    sub = decode_token(cred.credentials)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    school_id = parse_school_id(sub)
    if school_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid school token",
        )
    repo = SqlSchoolRepository(db)
    school = repo.get_by_id(school_id)
    if school is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="School not found",
        )
    if not school.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="School account disabled",
        )
    return school


def get_current_account(
    db: Session = Depends(get_db),
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | School:
    if cred is None or not cred.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    sub = decode_token(cred.credentials)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    school_id = parse_school_id(sub)
    if school_id is not None:
        repo = SqlSchoolRepository(db)
        school = repo.get_by_id(school_id)
        if school is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="School not found",
            )
        if not school.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="School account disabled",
            )
        return school
        
    uid = parse_user_id(sub)
    if uid is not None:
        user_repo = SqlUserRepository(db)
        user = user_repo.get_by_id(uid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account disabled",
            )
        return user
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token subject",
    )


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return user


def require_prof(
    user: User = Depends(get_current_user),
) -> User:
    if user.role not in ("prof", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Professor access only",
        )
    return user


def require_student(
    user: User = Depends(get_current_user),
) -> User:
    if user.role not in ("user", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access only",
        )
    return user


def require_player(
    user: User = Depends(get_current_user),
) -> User:
    if user.role not in ("user", "prof", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Player access only",
        )
    return user


def get_admin_user_repo(
    db: Session = Depends(get_db),
) -> IAdminUserRepository:
    return SqlAdminUserRepository(db)


def get_lesson_repo(db: Session = Depends(get_db)) -> ILessonRepository:
    return SqlLessonRepository(db)


def get_quiz_repo(db: Session = Depends(get_db)) -> IQuizRepository:
    return SqlQuizRepository(db)


def get_story_repo(db: Session = Depends(get_db)) -> IStoryRepository:
    return SqlStoryRepository(db)


def get_media_asset_repo(db: Session = Depends(get_db)) -> IMediaAssetRepository:
    return SqlMediaAssetRepository(db)


def get_media_asset_service(
    assets: IMediaAssetRepository = Depends(get_media_asset_repo),
) -> MediaAssetService:
    return MediaAssetService(assets, get_settings())


def get_contact_repo(db: Session = Depends(get_db)) -> IContactRepository:
    return SqlContactRepository(db)


def get_admin_progress_repo(
    db: Session = Depends(get_db),
) -> IAdminProgressRepository:
    return SqlAdminProgressRepository(db)


def get_multiplayer_repo(
    db: Session = Depends(get_db),
) -> IMultiplayerRepository:
    return SqlMultiplayerRepository(db)


def get_learning_path_repo(
    db: Session = Depends(get_db),
) -> ILearningPathRepository:
    return SqlLearningPathRepository(db)


def get_student_progress_repo(
    db: Session = Depends(get_db),
) -> IStudentProgressRepository:
    return SqlStudentProgressRepository(db)


def get_student_review_repo(
    db: Session = Depends(get_db),
) -> IStudentReviewRepository:
    return SqlStudentReviewRepository(db)


def get_game_repo(db: Session = Depends(get_db)) -> IGameRepository:
    return SqlGameRepository(db)


def get_delf_test_repo(db: Session = Depends(get_db)) -> IDelfTestRepository:
    return SqlDelfTestRepository(db)


def get_delf_mock_exam_repo(
    db: Session = Depends(get_db),
) -> IDelfMockExamRepository:
    return SqlDelfMockExamRepository(db)


def get_delf_mock_attempt_repo(
    db: Session = Depends(get_db),
) -> IDelfMockAttemptRepository:
    return SqlDelfMockAttemptRepository(db)


def get_difficulty_service() -> DifficultyService:
    return DifficultyService()


def get_student_stats_service(
    progress_repo: IStudentProgressRepository = Depends(get_student_progress_repo),
) -> StudentStatsService:
    return StudentStatsService(progress_repo)


def get_parcours_service(
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
    student_progress: IStudentProgressRepository = Depends(get_student_progress_repo),
    stats_service: StudentStatsService = Depends(get_student_stats_service),
    progress_service: ProgressService = Depends(get_progress_service),
    difficulty_service: DifficultyService = Depends(get_difficulty_service),
    delf_tests: IDelfTestRepository = Depends(get_delf_test_repo),
    users: IUserRepository = Depends(get_user_repo),
    quiz: IQuizRepository = Depends(get_quiz_repo),
    reviews: IStudentReviewRepository = Depends(get_student_review_repo),
) -> ParcoursService:
    return ParcoursService(
        paths=paths,
        student_progress=student_progress,
        stats_service=stats_service,
        progress_service=progress_service,
        difficulty_service=difficulty_service,
        delf_tests=delf_tests,
        users=users,
        quiz=quiz,
        reviews=reviews,
    )


def get_ai_parcours_assignment_service(
    ai: AIContentService = Depends(get_ai_content_service),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
    lessons: ILessonRepository = Depends(get_lesson_repo),
    stories: IStoryRepository = Depends(get_story_repo),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
    users: IUserRepository = Depends(get_user_repo),
) -> AIParcoursAssignmentService:
    return AIParcoursAssignmentService(
        ai=ai,
        paths=paths,
        lessons=lessons,
        stories=stories,
        quizzes=quizzes,
        users=users,
    )


def get_game_session_service(
    rooms: IMultiplayerRepository = Depends(get_multiplayer_repo),
    games: IGameRepository = Depends(get_game_repo),
    quiz: IQuizRepository = Depends(get_quiz_repo),
    users: IUserRepository = Depends(get_user_repo),
    stats_service: StudentStatsService = Depends(get_student_stats_service),
    difficulty_service: DifficultyService = Depends(get_difficulty_service),
) -> GameSessionService:
    return GameSessionService(
        rooms=rooms,
        games=games,
        quiz=quiz,
        users=users,
        stats_service=stats_service,
        difficulty_service=difficulty_service,
    )


def get_delf_test_service(
    delf_tests: IDelfTestRepository = Depends(get_delf_test_repo),
    quiz: IQuizRepository = Depends(get_quiz_repo),
    progress: IProgressRepository = Depends(get_progress_repo),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
    users: IUserRepository = Depends(get_user_repo),
    ai_parcours: AIParcoursAssignmentService = Depends(get_ai_parcours_assignment_service),
    reviews: IStudentReviewRepository = Depends(get_student_review_repo),
) -> DelfTestService:
    return DelfTestService(
        delf_tests=delf_tests,
        quiz=quiz,
        progress=progress,
        paths=paths,
        users=users,
        ai_parcours=ai_parcours,
        reviews=reviews,
    )


def get_student_service(
    reviews: IStudentReviewRepository = Depends(get_student_review_repo),
    progress: IStudentProgressRepository = Depends(get_student_progress_repo),
    stats_service: StudentStatsService = Depends(get_student_stats_service),
    parcours: ParcoursService = Depends(get_parcours_service),
    delf_tests: IDelfTestRepository = Depends(get_delf_test_repo),
    delf_service: DelfTestService = Depends(get_delf_test_service),
    ai: AIContentService = Depends(get_ai_content_service),
) -> StudentService:
    return StudentService(
        reviews=reviews,
        progress=progress,
        stats=stats_service,
        parcours=parcours,
        delf_tests=delf_tests,
        delf_service=delf_service,
        ai=ai,
    )


def get_delf_mock_exam_service(
    exams: IDelfMockExamRepository = Depends(get_delf_mock_exam_repo),
) -> DelfMockExamService:
    return DelfMockExamService(exams=exams)


def get_student_delf_mock_exam_service(
    exams: IDelfMockExamRepository = Depends(get_delf_mock_exam_repo),
    attempts: IDelfMockAttemptRepository = Depends(get_delf_mock_attempt_repo),
    reviews: IStudentReviewRepository = Depends(get_student_review_repo),
) -> StudentDelfMockExamService:
    return StudentDelfMockExamService(
        exams=exams,
        attempts=attempts,
        reviews=reviews,
    )
