from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_admin_progress_repo,
    get_admin_user_repo,
    get_auth_service,
    get_contact_repo,
    get_delf_test_service,
    get_game_repo,
    get_learning_path_repo,
    get_lesson_repo,
    get_multiplayer_repo,
    get_parcours_service,
    get_quiz_repo,
    get_school_repo,
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
    SetupStatusOut,
    QuizQuestionCreateIn,
    QuizQuestionOut,
    QuizQuestionUpdateIn,
    StoryCreateIn,
    StoryOut,
    StoryUpdateIn,
    UserProgressItemOut,
)
from app.api.schemas.multiplayer import GameCreateIn, GameOut, GameUpdateIn
from app.api.schemas.delf_test import (
    DelfLevelThresholdIn,
    DelfTestConfigOut,
    DelfTestConfigUpdateIn,
    DelfTestResultsOut,
    DelfTestSessionAdminOut,
    DelfTestTemplateCreateIn,
    DelfTestTemplateOut,
    DelfTestTemplateUpdateIn,
)
from app.api.schemas.parcours import (
    LearningPathCreateIn,
    LearningPathOut,
    ParcoursOut,
    ParcoursStepOut,
    LearningPathStepCreateIn,
    LearningPathStepOut,
    LearningPathStepUpdateIn,
    LearningPathUpdateIn,
)
from app.api.schemas.school import SchoolCreate, SchoolCreateOut, SchoolOut, SchoolUpdate
from app.application.auth_service import AuthError, AuthService
from app.application.delf_test_service import DelfTestError, DelfTestService
from app.application.parcours_service import ParcoursError, ParcoursService
from app.core.email_validation import InvalidEmailError, validate_real_email
from app.core.security import hash_password
from app.domain.constants import DELF_LEVELS
from app.domain.entities import User
from app.domain.ports import (
    IAdminProgressRepository,
    IAdminUserRepository,
    IContactRepository,
    IGameRepository,
    ILearningPathRepository,
    ILessonRepository,
    IMultiplayerRepository,
    IQuizRepository,
    ISchoolRepository,
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
    schools: ISchoolRepository = Depends(get_school_repo),
) -> AdminStatsOut:
    return AdminStatsOut(
        totalUsers=users.count_users(),
        activeUsers=users.count_active_users(),
        totalLessons=lessons.count(),
        totalQuizQuestions=quizzes.count(),
        totalStories=stories.count(),
        unreadMessages=contact.count_unread(),
        multiplayerRooms=rooms.count(),
        totalSchools=schools.count(),
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
    school_repo: ISchoolRepository = Depends(get_school_repo),
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
    if school_repo.get_by_email(normalized_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet e-mail est déjà utilisé par un établissement",
        )
    h = hash_password(body.password)
    try:
        u = admin_users.create_user_with_role(
            email=normalized_email,
            password_hash=h,
            first_name=body.firstName,
            last_name=body.lastName,
            level=body.level,
            role=body.role,
            phone=body.phone,
            date_of_birth=body.dateOfBirth,
            class_level=body.classLevel,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail déjà utilisé",
        ) from exc
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
        class_level=body.classLevel,
        phone=body.phone,
        date_of_birth=body.dateOfBirth,
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
    category: str | None = None,
    level: str | None = None,
    _admin: User = Depends(require_admin),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> list[QuizQuestionOut]:
    items = quizzes.list_all()
    if category:
        items = [x for x in items if x.category == category]
    if level:
        items = [x for x in items if x.level == level]
    return [QuizQuestionOut.from_domain(x) for x in items]


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


# --- Learning paths ---


def _learning_path_out(
    path, paths: ILearningPathRepository
) -> LearningPathOut:
    return LearningPathOut(
        id=path.id,
        classLevel=path.class_level,
        title=path.title,
        description=path.description,
        delfTargetLevel=path.delf_target_level,
        isActive=path.is_active,
        minScore=path.min_score,
        maxScore=path.max_score,
        isDefault=path.is_default,
        stepCount=paths.count_steps(path.id),
        assignedUsersCount=paths.count_assigned_users(path.id),
        createdAt=path.created_at,
    )


def _validate_learning_path_payload(
    paths: ILearningPathRepository,
    *,
    class_level: str,
    delf_target_level: str,
    min_score: int | None,
    max_score: int | None,
    is_default: bool,
    exclude_id: UUID | None = None,
) -> None:
    if delf_target_level not in DELF_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Objectif DELF invalide.",
        )
    if min_score is not None and max_score is not None and min_score > max_score:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le score minimum ne peut pas dépasser le score maximum.",
        )
    if is_default:
        conflict = next(
            (
                path
                for path in paths.list_all()
                if path.class_level == class_level
                and path.is_default
                and path.id != exclude_id
            ),
            None,
        )
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Un parcours par défaut existe déjà pour {class_level}. "
                    "Désactivez-le avant d'en définir un autre."
                ),
            )


def _parcours_out(data: dict) -> ParcoursOut:
    path = data["path"]
    steps = data["steps"]
    stats = data["stats"]
    total_steps = len(steps)
    completed_steps = sum(1 for s in steps if s["status"] == "completed")
    completion_percent = (
        round(completed_steps / total_steps * 100, 1) if total_steps else 0.0
    )
    return ParcoursOut(
        pathId=path.id,
        assignedPathId=path.id,
        title=path.title,
        description=path.description,
        classLevel=path.class_level,
        delfTargetLevel=path.delf_target_level,
        totalXp=stats.total_xp,
        currentStreak=stats.current_streak,
        preferredDifficulty=stats.preferred_difficulty,
        completionPercent=completion_percent,
        steps=[
            ParcoursStepOut(
                id=s["step"].id,
                stepOrder=s["step"].step_order,
                stepType=s["step"].step_type,
                title=s["step"].title,
                xpReward=s["step"].xp_reward,
                status=s["status"],
                quizCategory=s["step"].quiz_category,
                lessonId=s["step"].lesson_id,
                storyId=s["step"].story_id,
                requiredStepId=s["step"].required_step_id,
                score=s["progress"].score if s["progress"] else None,
                attempts=s["progress"].attempts if s["progress"] else 0,
            )
            for s in steps
        ],
    )


def _validate_step_payload(
    *,
    step_type: str,
    quiz_category: str | None,
    lesson_id: UUID | None,
    story_id: UUID | None,
) -> None:
    if step_type not in {"lesson", "quiz", "story"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Type d'étape invalide.",
        )
    if step_type == "lesson" and lesson_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Une étape leçon doit référencer une leçon.",
        )
    if step_type == "quiz" and not quiz_category:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Une étape quiz doit définir une catégorie.",
        )
    if step_type == "story" and story_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Une étape histoire doit référencer une histoire.",
        )


@router.get("/learning-paths", response_model=list[LearningPathOut])
def list_learning_paths(
    _admin: User = Depends(require_admin),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
) -> list[LearningPathOut]:
    return [_learning_path_out(p, paths) for p in paths.list_all()]


@router.post(
    "/learning-paths",
    response_model=LearningPathOut,
    status_code=status.HTTP_201_CREATED,
)
def create_learning_path(
    body: LearningPathCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
) -> LearningPathOut:
    _validate_learning_path_payload(
        paths,
        class_level=body.classLevel,
        delf_target_level=body.delfTargetLevel,
        min_score=body.minScore,
        max_score=body.maxScore,
        is_default=body.isDefault,
    )
    try:
        path = paths.create_path(
            class_level=body.classLevel,
            title=body.title,
            delf_target_level=body.delfTargetLevel,
            description=body.description,
            min_score=body.minScore,
            max_score=body.maxScore,
            is_default=body.isDefault,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de créer ce parcours DELF.",
        ) from exc
    return _learning_path_out(path, paths)


@router.put("/learning-paths/{path_id}", response_model=LearningPathOut)
def update_learning_path(
    path_id: UUID,
    body: LearningPathUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
) -> LearningPathOut:
    current = paths.get(path_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    next_class_level = current.class_level
    next_min = body.minScore if "minScore" in body.model_fields_set else current.min_score
    next_max = body.maxScore if "maxScore" in body.model_fields_set else current.max_score
    next_delf_target = (
        body.delfTargetLevel
        if "delfTargetLevel" in body.model_fields_set and body.delfTargetLevel is not None
        else current.delf_target_level
    )
    next_default = (
        body.isDefault if "isDefault" in body.model_fields_set else current.is_default
    )
    _validate_learning_path_payload(
        paths,
        class_level=next_class_level,
        delf_target_level=next_delf_target,
        min_score=next_min,
        max_score=next_max,
        is_default=bool(next_default),
        exclude_id=path_id,
    )
    updated = paths.update_path(
        path_id,
        title=body.title,
        description=body.description,
        delf_target_level=body.delfTargetLevel,
        is_active=body.isActive,
        min_score=next_min,
        max_score=next_max,
        is_default=body.isDefault,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return _learning_path_out(updated, paths)


@router.get("/users/{user_id}/parcours", response_model=ParcoursOut)
def get_admin_user_parcours(
    user_id: UUID,
    _admin: User = Depends(require_admin),
    users: IUserRepository = Depends(get_user_repo),
    svc: ParcoursService = Depends(get_parcours_service),
) -> ParcoursOut:
    student = users.get_by_id(user_id)
    if student is None or student.role != "user":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable")
    try:
        data = svc.get_parcours_for_user(student)
    except ParcoursError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    return _parcours_out(data)


@router.delete("/learning-paths/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_learning_path(
    path_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
) -> None:
    if not paths.delete_path(path_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


@router.get("/learning-paths/{path_id}/steps", response_model=list[LearningPathStepOut])
def list_learning_path_steps(
    path_id: UUID,
    _admin: User = Depends(require_admin),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
) -> list[LearningPathStepOut]:
    return [
        LearningPathStepOut(
            id=s.id,
            pathId=s.path_id,
            stepOrder=s.step_order,
            stepType=s.step_type,
            title=s.title,
            xpReward=s.xp_reward,
            quizCategory=s.quiz_category,
            lessonId=s.lesson_id,
            storyId=s.story_id,
            requiredStepId=s.required_step_id,
            createdAt=s.created_at,
        )
        for s in paths.list_steps(path_id)
    ]


@router.post(
    "/learning-paths/{path_id}/steps",
    response_model=LearningPathStepOut,
    status_code=status.HTTP_201_CREATED,
)
def create_learning_path_step(
    path_id: UUID,
    body: LearningPathStepCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
) -> LearningPathStepOut:
    if paths.get(path_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _validate_step_payload(
        step_type=body.stepType,
        quiz_category=body.quizCategory,
        lesson_id=body.lessonId,
        story_id=body.storyId,
    )
    step = paths.create_step(
        path_id=path_id,
        step_order=body.stepOrder,
        step_type=body.stepType,
        title=body.title,
        xp_reward=body.xpReward,
        quiz_category=body.quizCategory,
        lesson_id=body.lessonId,
        story_id=body.storyId,
        required_step_id=body.requiredStepId,
    )
    db.commit()
    return LearningPathStepOut(
        id=step.id,
        pathId=step.path_id,
        stepOrder=step.step_order,
        stepType=step.step_type,
        title=step.title,
        xpReward=step.xp_reward,
        quizCategory=step.quiz_category,
        lessonId=step.lesson_id,
        storyId=step.story_id,
        requiredStepId=step.required_step_id,
        createdAt=step.created_at,
    )


@router.put(
    "/learning-paths/{path_id}/steps/{step_id}",
    response_model=LearningPathStepOut,
)
def update_learning_path_step(
    path_id: UUID,
    step_id: UUID,
    body: LearningPathStepUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
) -> LearningPathStepOut:
    existing = paths.get_step(step_id)
    if existing is None or existing.path_id != path_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    next_step_type = body.stepType if body.stepType is not None else existing.step_type
    next_quiz_category = (
        body.quizCategory if body.quizCategory is not None else existing.quiz_category
    )
    next_lesson_id = body.lessonId if body.lessonId is not None else existing.lesson_id
    next_story_id = body.storyId if body.storyId is not None else existing.story_id
    _validate_step_payload(
        step_type=next_step_type,
        quiz_category=next_quiz_category,
        lesson_id=next_lesson_id,
        story_id=next_story_id,
    )
    updated = paths.update_step(
        step_id,
        step_order=body.stepOrder,
        step_type=body.stepType,
        title=body.title,
        xp_reward=body.xpReward,
        quiz_category=body.quizCategory,
        lesson_id=body.lessonId,
        story_id=body.storyId,
        required_step_id=body.requiredStepId,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return LearningPathStepOut(
        id=updated.id,
        pathId=updated.path_id,
        stepOrder=updated.step_order,
        stepType=updated.step_type,
        title=updated.title,
        xpReward=updated.xp_reward,
        quizCategory=updated.quiz_category,
        lessonId=updated.lesson_id,
        storyId=updated.story_id,
        requiredStepId=updated.required_step_id,
        createdAt=updated.created_at,
    )


@router.delete(
    "/learning-paths/{path_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_learning_path_step(
    path_id: UUID,
    step_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    paths: ILearningPathRepository = Depends(get_learning_path_repo),
) -> None:
    existing = paths.get_step(step_id)
    if existing is None or existing.path_id != path_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not paths.delete_step(step_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()


# --- Games catalog ---


@router.get("/games", response_model=list[GameOut])
def list_games(
    _admin: User = Depends(require_admin),
    games: IGameRepository = Depends(get_game_repo),
) -> list[GameOut]:
    return [
        GameOut(
            id=g.id,
            slug=g.slug,
            name=g.name,
            description=g.description,
            minPlayers=g.min_players,
            maxPlayers=g.max_players,
            defaultQuestionCount=g.default_question_count,
        )
        for g in games.list_games(active_only=False)
    ]


@router.post("/games", response_model=GameOut, status_code=status.HTTP_201_CREATED)
def create_game(
    body: GameCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    games: IGameRepository = Depends(get_game_repo),
) -> GameOut:
    game = games.create_game(
        slug=body.slug,
        name=body.name,
        min_players=body.minPlayers,
        max_players=body.maxPlayers,
        default_question_count=body.defaultQuestionCount,
        description=body.description,
    )
    db.commit()
    return GameOut(
        id=game.id,
        slug=game.slug,
        name=game.name,
        description=game.description,
        minPlayers=game.min_players,
        maxPlayers=game.max_players,
        defaultQuestionCount=game.default_question_count,
    )


@router.put("/games/{game_id}", response_model=GameOut)
def update_game(
    game_id: UUID,
    body: GameUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    games: IGameRepository = Depends(get_game_repo),
) -> GameOut:
    if (
        body.minPlayers is not None
        and body.maxPlayers is not None
        and body.minPlayers > body.maxPlayers
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="minPlayers cannot exceed maxPlayers",
        )
    updated = games.update_game(
        game_id,
        name=body.name,
        min_players=body.minPlayers,
        max_players=body.maxPlayers,
        default_question_count=body.defaultQuestionCount,
        description=body.description,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.commit()
    return GameOut(
        id=updated.id,
        slug=updated.slug,
        name=updated.name,
        description=updated.description,
        minPlayers=updated.min_players,
        maxPlayers=updated.max_players,
        defaultQuestionCount=updated.default_question_count,
    )


# --- Schools ---


@router.get("/schools", response_model=list[SchoolOut])
def list_schools(
    _admin: User = Depends(require_admin),
    schools: ISchoolRepository = Depends(get_school_repo),
) -> list[SchoolOut]:
    return [SchoolOut.from_domain(s) for s in schools.list_all()]


@router.post("/schools", response_model=SchoolCreateOut, status_code=status.HTTP_201_CREATED)
def create_school(
    body: SchoolCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    auth: AuthService = Depends(get_auth_service),
) -> SchoolCreateOut:
    try:
        school, plain_password = auth.create_school_account(
            name=body.name,
            email=body.email,
            admin_id=admin.id,
            address=body.address,
            city=body.city,
            postal_code=body.postalCode,
            phone=body.phone,
            director_name=body.directorName,
        )
        db.commit()
    except AuthError as exc:
        db.rollback()
        if exc.code == "email_taken":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=exc.message
            ) from exc
        if exc.code == "invalid_email":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet e-mail est déjà utilisé",
        ) from exc
    return SchoolCreateOut.from_domain(school, plain_password)


@router.get("/schools/{school_id}", response_model=SchoolOut)
def get_school(
    school_id: UUID,
    _admin: User = Depends(require_admin),
    schools: ISchoolRepository = Depends(get_school_repo),
) -> SchoolOut:
    school = schools.get_by_id(school_id)
    if school is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="École introuvable")
    return SchoolOut.from_domain(school)


@router.put("/schools/{school_id}", response_model=SchoolOut)
def update_school(
    school_id: UUID,
    body: SchoolUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    schools: ISchoolRepository = Depends(get_school_repo),
) -> SchoolOut:
    school = schools.update(
        school_id,
        name=body.name,
        address=body.address,
        city=body.city,
        postal_code=body.postalCode,
        phone=body.phone,
        director_name=body.directorName,
        is_active=body.isActive,
    )
    if school is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="École introuvable")
    db.commit()
    return SchoolOut.from_domain(school)


@router.delete("/schools/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school(
    school_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    schools: ISchoolRepository = Depends(get_school_repo),
) -> None:
    if not schools.delete(school_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="École introuvable")
    db.commit()


@router.get("/schools/{school_id}/students", response_model=list[AdminUserOut])
def list_school_students(
    school_id: UUID,
    _admin: User = Depends(require_admin),
    schools: ISchoolRepository = Depends(get_school_repo),
) -> list[AdminUserOut]:
    school = schools.get_by_id(school_id)
    if school is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="École introuvable")
    return [AdminUserOut.from_domain(u) for u in schools.list_students(school_id)]


@router.get("/schools/{school_id}/professors", response_model=list[AdminUserOut])
def list_school_professors(
    school_id: UUID,
    _admin: User = Depends(require_admin),
    schools: ISchoolRepository = Depends(get_school_repo),
) -> list[AdminUserOut]:
    school = schools.get_by_id(school_id)
    if school is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="École introuvable")
    return [AdminUserOut.from_domain(u) for u in schools.list_professors(school_id)]


# --- DELF level tests ---


@router.get("/delf-tests", response_model=list[DelfTestSessionAdminOut])
def admin_list_delf_tests(
    userId: UUID | None = None,
    classLevel: str | None = None,
    status: str | None = None,
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
    users: IUserRepository = Depends(get_user_repo),
) -> list[DelfTestSessionAdminOut]:
    sessions = service.list_all_sessions(
        user_id=userId,
        class_level=classLevel,
        status=status,
    )
    result: list[DelfTestSessionAdminOut] = []
    for session in sessions:
        student = users.get_by_id(session.user_id)
        result.append(
            DelfTestSessionAdminOut(
                sessionId=session.id,
                userId=session.user_id,
                classLevel=session.class_level,
                targetDelfLevel=session.target_delf_level,
                achievedDelfLevel=session.achieved_delf_level,
                overallScore=session.overall_score,
                categoryScores=session.category_scores,
                status=session.status,
                startedAt=session.started_at,
                finishedAt=session.finished_at,
                studentFirstName=student.first_name if student else None,
                studentLastName=student.last_name if student else None,
                studentEmail=student.email if student else None,
            )
        )
    return result


@router.get("/delf-tests/{session_id}")
def admin_get_delf_test(
    session_id: UUID,
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
) -> dict:
    try:
        return service.get_admin_session(session_id)
    except DelfTestError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc


@router.get("/delf-test-config", response_model=DelfTestConfigOut)
def admin_get_delf_test_config(
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestConfigOut:
    config = service.get_config()
    return DelfTestConfigOut(
        questionsPerCategory=config.questions_per_category,
        levelThresholds=[
            DelfLevelThresholdIn.model_validate(t) for t in config.level_thresholds
        ],
        updatedAt=config.updated_at,
    )


@router.put("/delf-test-config", response_model=DelfTestConfigOut)
def admin_update_delf_test_config(
    body: DelfTestConfigUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestConfigOut:
    try:
        thresholds = None
        if body.levelThresholds is not None:
            thresholds = [t.model_dump(by_alias=True) for t in body.levelThresholds]
        config = service.update_config(
            questions_per_category=body.questionsPerCategory,
            level_thresholds=thresholds,
        )
        db.commit()
        return DelfTestConfigOut(
            questionsPerCategory=config.questions_per_category,
            levelThresholds=[
                DelfLevelThresholdIn.model_validate(t) for t in config.level_thresholds
            ],
            updatedAt=config.updated_at,
        )
    except DelfTestError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc


@router.get("/delf-test-templates", response_model=list[DelfTestTemplateOut])
def admin_list_delf_test_templates(
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
) -> list[DelfTestTemplateOut]:
    return [
        DelfTestTemplateOut.model_validate(item)
        for item in service.list_templates()
    ]


@router.get("/delf-test-templates/{template_id}", response_model=DelfTestTemplateOut)
def admin_get_delf_test_template(
    template_id: UUID,
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestTemplateOut:
    try:
        return DelfTestTemplateOut.model_validate(service.get_template(template_id))
    except DelfTestError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


@router.post(
    "/delf-test-templates",
    response_model=DelfTestTemplateOut,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_delf_test_template(
    body: DelfTestTemplateCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestTemplateOut:
    try:
        result = service.create_template(
            name=body.name,
            description=body.description,
            class_level=body.classLevel,
            target_delf_level=body.targetDelfLevel,
            is_active=body.isActive,
            question_ids_by_category={
                category: [str(qid) for qid in ids]
                for category, ids in body.questionIdsByCategory.items()
            },
        )
        db.commit()
        return DelfTestTemplateOut.model_validate(result)
    except DelfTestError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@router.put("/delf-test-templates/{template_id}", response_model=DelfTestTemplateOut)
def admin_update_delf_test_template(
    template_id: UUID,
    body: DelfTestTemplateUpdateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestTemplateOut:
    try:
        questions = None
        if body.questionIdsByCategory is not None:
            questions = {
                category: [str(qid) for qid in ids]
                for category, ids in body.questionIdsByCategory.items()
            }
        result = service.update_template(
            template_id,
            name=body.name,
            description=body.description if "description" in body.model_fields_set else None,
            class_level=body.classLevel,
            target_delf_level=body.targetDelfLevel,
            is_active=body.isActive,
            question_ids_by_category=questions,
        )
        db.commit()
        return DelfTestTemplateOut.model_validate(result)
    except DelfTestError as exc:
        db.rollback()
        status_code = status.HTTP_404_NOT_FOUND if "introuvable" in exc.message else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=exc.message) from exc


@router.delete(
    "/delf-test-templates/{template_id}",
    response_model=DelfTestTemplateOut,
)
def admin_disable_delf_test_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestTemplateOut:
    try:
        result = service.disable_template(template_id)
        db.commit()
        return DelfTestTemplateOut.model_validate(result)
    except DelfTestError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


# --- One-time admin bootstrap ---


@router.get("/setup/status", response_model=SetupStatusOut)
def admin_setup_status(
    admin_users: IAdminUserRepository = Depends(get_admin_user_repo),
) -> SetupStatusOut:
    return SetupStatusOut(setupComplete=admin_users.count_admins() > 0)


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
        phone=body.phone,
        date_of_birth=body.dateOfBirth,
    )
    db.commit()
    return AdminUserOut.from_domain(u)
