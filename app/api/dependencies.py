from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.auth_service import AuthService
from app.application.progress_service import ProgressService
from app.core.config import get_settings
from app.core.security import decode_token, parse_school_id, parse_user_id
from app.domain.entities import School, User
from app.domain.ports import (
    IAdminProgressRepository,
    IAdminUserRepository,
    IContactRepository,
    IEmailSender,
    ILessonRepository,
    IMultiplayerRepository,
    IProgressRepository,
    IQuizRepository,
    IRecommendationRepository,
    ISchoolRepository,
    IStoryRepository,
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
from app.infrastructure.repositories.sql_lesson_repository import SqlLessonRepository
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
