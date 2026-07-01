from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_admin_progress_repo,
    get_admin_user_repo,
    get_contact_repo,
    get_lesson_repo,
    get_multiplayer_repo,
    get_quiz_repo,
    get_story_repo,
    get_user_repo,
    require_admin,
)
from app.api.schemas.admin import (
    AdminSetupIn,
    AdminStatsOut,
    AdminUserCreateIn,
    AdminUserOut,
    AdminUserUpdateIn,
    ContactMessageOut,
    LessonCreateIn,
    LessonOut,
    LessonUpdateIn,
    MultiplayerRoomOut,
    QuizQuestionCreateIn,
    QuizQuestionOut,
    QuizQuestionUpdateIn,
    StoryCreateIn,
    StoryOut,
    StoryUpdateIn,
    UserProgressItemOut,
)
from app.core.email_validation import InvalidEmailError, validate_real_email
from app.core.security import hash_password
from app.domain.entities import User
from app.domain.ports import (
    IAdminProgressRepository,
    IAdminUserRepository,
    IContactRepository,
    ILessonRepository,
    IMultiplayerRepository,
    IQuizRepository,
    IStoryRepository,
    IUserRepository,
)
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStatsOut)
def admin_stats(
    _admin: User = Depends(require_admin),
    users: IAdminUserRepository = Depends(get_admin_user_repo),
    lessons: ILessonRepository = Depends(get_lesson_repo),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
    stories: IStoryRepository = Depends(get_story_repo),
    contact: IContactRepository = Depends(get_contact_repo),
    rooms: IMultiplayerRepository = Depends(get_multiplayer_repo),
) -> AdminStatsOut:
    return AdminStatsOut(
        totalUsers=users.count_users(),
        activeUsers=users.count_active_users(),
        totalLessons=lessons.count(),
        totalQuizQuestions=quizzes.count(),
        totalStories=stories.count(),
        unreadMessages=contact.count_unread(),
        multiplayerRooms=rooms.count(),
        usersByLevel=users.count_by_level(),
        lessonsByCategory=lessons.count_by_category(),
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    _admin: User = Depends(require_admin),
    users: IAdminUserRepository = Depends(get_admin_user_repo),
) -> list[AdminUserOut]:
    return [AdminUserOut.from_domain(u) for u in users.list_users()]


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: AdminUserCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    admin_users: IAdminUserRepository = Depends(get_admin_user_repo),
    user_repo: IUserRepository = Depends(get_user_repo),
) -> AdminUserOut:
    try:
        normalized_email = validate_real_email(body.email)
    except InvalidEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        ) from exc
    if user_repo.get_by_email(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail déjà utilisé",
        )
    h = hash_password(body.password)
    u = admin_users.create_user_with_role(
        email=normalized_email,
        password_hash=h,
        first_name=body.firstName,
        last_name=body.lastName,
        level=body.level,
        role=body.role,
    )
    db.commit()
    return AdminUserOut.from_domain(u)


@router.put("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: UUID,
    body: AdminUserUpdateIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    users: IAdminUserRepository = Depends(get_admin_user_repo),
) -> AdminUserOut:
    if user_id == admin.id and body.isActive is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate yourself",
        )
    if user_id == admin.id and body.role is not None and body.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role",
        )
    u = users.update_user(
        user_id,
        role=body.role,
        level=body.level,
        is_active=body.isActive,
    )
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return AdminUserOut.from_domain(u)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    users: IAdminUserRepository = Depends(get_admin_user_repo),
) -> None:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself",
        )
    if not users.delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


# --- Lessons ---


@router.get("/lessons", response_model=list[LessonOut])
def list_lessons(
    _admin: User = Depends(require_admin),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> list[LessonOut]:
    return [LessonOut.from_domain(x) for x in lessons.list_all()]


@router.post("/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_lesson(
    body: LessonCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> LessonOut:
    l = lessons.create(
        title=body.title,
        content=body.content,
        category=body.category,
        level=body.level,
        sort_order=body.sortOrder,
    )
    db.commit()
    return LessonOut.from_domain(l)


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(
    lesson_id: UUID,
    body: LessonUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> LessonOut:
    l = lessons.update(
        lesson_id,
        title=body.title,
        content=body.content,
        category=body.category,
        level=body.level,
        sort_order=body.sortOrder,
    )
    if l is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return LessonOut.from_domain(l)


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> None:
    if not lessons.delete(lesson_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


# --- Quiz questions ---


@router.get("/quiz-questions", response_model=list[QuizQuestionOut])
def list_quiz_questions(
    _admin: User = Depends(require_admin),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> list[QuizQuestionOut]:
    return [QuizQuestionOut.from_domain(x) for x in quizzes.list_all()]


@router.post(
    "/quiz-questions",
    response_model=QuizQuestionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz_question(
    body: QuizQuestionCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> QuizQuestionOut:
    if body.correctIndex < 0 or body.correctIndex >= len(body.options):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correctIndex out of range",
        )
    q = quizzes.create(
        question=body.question,
        options=body.options,
        correct_index=body.correctIndex,
        explanation=body.explanation,
        category=body.category,
        level=body.level,
    )
    db.commit()
    return QuizQuestionOut.from_domain(q)


@router.put("/quiz-questions/{question_id}", response_model=QuizQuestionOut)
def update_quiz_question(
    question_id: UUID,
    body: QuizQuestionUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> QuizQuestionOut:
    opts = body.options
    current = quizzes.get(question_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    n_opts = list(opts) if opts is not None else current.options
    idx = body.correctIndex if body.correctIndex is not None else current.correct_index
    if idx < 0 or idx >= len(n_opts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correctIndex out of range",
        )
    q = quizzes.update(
        question_id,
        question=body.question,
        options=body.options,
        correct_index=body.correctIndex,
        explanation=body.explanation,
        category=body.category,
        level=body.level,
    )
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return QuizQuestionOut.from_domain(q)


@router.delete("/quiz-questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> None:
    if not quizzes.delete(question_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


# --- Stories ---


@router.get("/stories", response_model=list[StoryOut])
def list_stories(
    _admin: User = Depends(require_admin),
    stories: IStoryRepository = Depends(get_story_repo),
) -> list[StoryOut]:
    return [StoryOut.from_domain(x) for x in stories.list_all()]


@router.post("/stories", response_model=StoryOut, status_code=status.HTTP_201_CREATED)
def create_story(
    body: StoryCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    stories: IStoryRepository = Depends(get_story_repo),
) -> StoryOut:
    s = stories.create(
        title=body.title,
        content=body.content,
        level=body.level,
        audio_url=body.audioUrl,
    )
    db.commit()
    return StoryOut.from_domain(s)


@router.put("/stories/{story_id}", response_model=StoryOut)
def update_story(
    story_id: UUID,
    body: StoryUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    stories: IStoryRepository = Depends(get_story_repo),
) -> StoryOut:
    s = stories.update(
        story_id,
        title=body.title,
        content=body.content,
        level=body.level,
        audio_url=body.audioUrl,
    )
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return StoryOut.from_domain(s)


@router.delete("/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(
    story_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    stories: IStoryRepository = Depends(get_story_repo),
) -> None:
    if not stories.delete(story_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


# --- Contact messages ---


class ContactMessageUpdateIn(BaseModel):
    read: bool = True
    model_config = ConfigDict(populate_by_name=True)


@router.get("/contact-messages", response_model=list[ContactMessageOut])
def list_contact_messages(
    _admin: User = Depends(require_admin),
    contact: IContactRepository = Depends(get_contact_repo),
) -> list[ContactMessageOut]:
    return [ContactMessageOut.from_domain(x) for x in contact.list_all()]


@router.put("/contact-messages/{message_id}", response_model=ContactMessageOut)
def update_contact_message(
    message_id: UUID,
    body: ContactMessageUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    contact: IContactRepository = Depends(get_contact_repo),
) -> ContactMessageOut:
    m = contact.mark_read(message_id, read=body.read)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return ContactMessageOut.from_domain(m)


@router.delete("/contact-messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    contact: IContactRepository = Depends(get_contact_repo),
) -> None:
    if not contact.delete(message_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


# --- Progress (read-only) ---


@router.get("/progress", response_model=list[UserProgressItemOut])
def list_progress(
    _admin: User = Depends(require_admin),
    progress: IAdminProgressRepository = Depends(get_admin_progress_repo),
) -> list[UserProgressItemOut]:
    rows = progress.list_all_with_users()
    return [UserProgressItemOut.from_row(r) for r in rows]


# --- Multiplayer rooms ---


@router.get("/multiplayer-rooms", response_model=list[MultiplayerRoomOut])
def list_multiplayer_rooms(
    _admin: User = Depends(require_admin),
    rooms: IMultiplayerRepository = Depends(get_multiplayer_repo),
) -> list[MultiplayerRoomOut]:
    return [MultiplayerRoomOut.from_domain(x) for x in rooms.list_all()]


# --- One-time admin bootstrap ---


@router.post("/setup", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def admin_setup(
    body: AdminSetupIn,
    db: Session = Depends(get_db),
    admin_users: IAdminUserRepository = Depends(get_admin_user_repo),
    user_repo: IUserRepository = Depends(get_user_repo),
) -> AdminUserOut:
    if admin_users.count_admins() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed",
        )
    try:
        normalized_email = validate_real_email(body.email)
    except InvalidEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        ) from exc
    if user_repo.get_by_email(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail déjà utilisé",
        )
    h = hash_password(body.password)
    u = admin_users.create_user_with_role(
        email=normalized_email,
        password_hash=h,
        first_name=body.firstName,
        last_name=body.lastName,
        level=body.level,
        role="admin",
    )
    db.commit()
    return AdminUserOut.from_domain(u)
