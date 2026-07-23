import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_lesson_repo,
    get_multiplayer_repo,
    get_parcours_service,
    get_delf_test_service,
    get_progress_repo,
    get_quiz_repo,
    get_recommendation_repo,
    get_school_repo,
    get_story_repo,
    require_prof,
)
from app.api.schemas.admin import (
    LessonCreateIn,
    LessonOut,
    MultiplayerRoomOut,
    QuizQuestionCreateIn,
    QuizQuestionOut,
    QuizQuestionUpdateIn,
    StoryCreateIn,
    StoryOut,
    StoryUpdateIn,
)
from app.api.schemas.parcours import ParcoursOut, ParcoursStepOut
from app.api.schemas.delf_test import DelfTestHistoryOut
from app.api.schemas.recommendation import RecommendationCreate, RecommendationOut
from app.application.delf_test_service import DelfTestService
from app.api.schemas.user import UserOut
from app.application.parcours_service import ParcoursError, ParcoursService
from app.domain.constants import ALLOWED_DIFFICULTIES
from app.domain.entities import User
from app.domain.ports import (
    ILessonRepository,
    IMultiplayerRepository,
    IProgressRepository,
    IQuizRepository,
    IRecommendationRepository,
    ISchoolRepository,
    IStoryRepository,
)
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/prof", tags=["professor"])

_ROOM_CODE_BYTES = 4


def _normalize_visibility(value: str | None, prof: User) -> str:
    visibility = value or "public"
    if visibility not in {"public", "school"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visibilité invalide.",
        )
    if visibility == "school" and prof.teacher_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas associé à un établissement.",
        )
    return visibility


class RoomCreateIn(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    classLevel: str = Field(min_length=1)
    participantIds: list[UUID] = Field(min_length=2)


class StudentGroupOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    classLevel: str
    students: list[UserOut]


def _student_group_key(student: User) -> str:
    return student.class_level or student.level or "Non classé"


def _build_room_data(class_level: str, students: list[User]) -> dict:
    participants = [
        {
            "id": str(student.id),
            "firstName": student.first_name,
            "lastName": student.last_name,
            "email": student.email,
            "classLevel": _student_group_key(student),
        }
        for student in students
    ]
    return {
        "classLevel": class_level,
        "participants": participants,
        "players": participants,
        "status": "waiting",
        "allowedDifficulties": list(ALLOWED_DIFFICULTIES),
    }


@router.get("/students", response_model=list[UserOut])
def list_students(
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
) -> list[UserOut]:
    if prof.teacher_school_id is None:
        return []
    students = school_repo.list_students(prof.teacher_school_id)
    return [UserOut.from_domain(s) for s in students]


@router.get("/students/{student_id}", response_model=UserOut)
def get_student(
    student_id: UUID,
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
) -> UserOut:
    if prof.teacher_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas associé à un établissement",
        )
    students = school_repo.list_students(prof.teacher_school_id)
    student = next((s for s in students if s.id == student_id), None)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Élève introuvable dans votre établissement",
        )
    return UserOut.from_domain(student)


@router.get("/students/{student_id}/progress")
def get_student_progress(
    student_id: UUID,
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    progress_repo: IProgressRepository = Depends(get_progress_repo),
) -> dict:
    if prof.teacher_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas associé à un établissement",
        )
    students = school_repo.list_students(prof.teacher_school_id)
    student = next((s for s in students if s.id == student_id), None)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Élève introuvable dans votre établissement",
        )
    progress = progress_repo.get_for_user(student_id)
    return {
        "student": UserOut.from_domain(student).model_dump(),
        "progress": progress.to_dict(),
    }


@router.get("/students/{student_id}/parcours", response_model=ParcoursOut)
def get_student_parcours(
    student_id: UUID,
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    svc: ParcoursService = Depends(get_parcours_service),
) -> ParcoursOut:
    if prof.teacher_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas associé à un établissement",
        )
    students = school_repo.list_students(prof.teacher_school_id)
    student = next((s for s in students if s.id == student_id), None)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Élève introuvable dans votre établissement",
        )
    try:
        data = svc.get_parcours_for_user(student)
    except ParcoursError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
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


@router.get("/students/{student_id}/delf-tests", response_model=list[DelfTestHistoryOut])
def get_student_delf_tests(
    student_id: UUID,
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    service: DelfTestService = Depends(get_delf_test_service),
) -> list[DelfTestHistoryOut]:
    if prof.teacher_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas associé à un établissement",
        )
    students = school_repo.list_students(prof.teacher_school_id)
    student = next((s for s in students if s.id == student_id), None)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Élève introuvable dans votre établissement",
        )
    items = service.list_student_history(student_id)
    return [DelfTestHistoryOut.model_validate(item) for item in items]


@router.get(
    "/students/{student_id}/recommendations",
    response_model=list[RecommendationOut],
)
def list_recommendations(
    student_id: UUID,
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    rec_repo: IRecommendationRepository = Depends(get_recommendation_repo),
) -> list[RecommendationOut]:
    if prof.teacher_school_id is not None:
        students = school_repo.list_students(prof.teacher_school_id)
        if not any(s.id == student_id for s in students):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Élève introuvable dans votre établissement",
            )
    recs = rec_repo.list_for_student(student_id)
    return [RecommendationOut.from_domain(r) for r in recs]


@router.post(
    "/students/{student_id}/recommendations",
    response_model=RecommendationOut,
    status_code=status.HTTP_201_CREATED,
)
def add_recommendation(
    student_id: UUID,
    body: RecommendationCreate,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    rec_repo: IRecommendationRepository = Depends(get_recommendation_repo),
) -> RecommendationOut:
    if prof.teacher_school_id is not None:
        students = school_repo.list_students(prof.teacher_school_id)
        if not any(s.id == student_id for s in students):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Élève introuvable dans votre établissement",
            )
    rec = rec_repo.create(
        student_id=student_id,
        professor_id=prof.id,
        content=body.content,
    )
    db.commit()
    return RecommendationOut.from_domain(rec)


@router.get("/student-groups", response_model=list[StudentGroupOut])
def list_student_groups(
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
) -> list[StudentGroupOut]:
    if prof.teacher_school_id is None:
        return []
    students = school_repo.list_students(prof.teacher_school_id)
    grouped: dict[str, list[User]] = {}
    for student in students:
        key = _student_group_key(student)
        grouped.setdefault(key, []).append(student)
    return [
        StudentGroupOut(
            classLevel=class_level,
            students=[UserOut.from_domain(s) for s in group_students],
        )
        for class_level, group_students in sorted(grouped.items())
    ]


@router.get("/multiplayer-rooms", response_model=list[MultiplayerRoomOut])
def list_multiplayer_rooms(
    prof: User = Depends(require_prof),
    rooms: IMultiplayerRepository = Depends(get_multiplayer_repo),
) -> list[MultiplayerRoomOut]:
    return [MultiplayerRoomOut.from_domain(r) for r in rooms.list_by_professor(prof.id)]


@router.post(
    "/multiplayer-rooms",
    response_model=MultiplayerRoomOut,
    status_code=status.HTTP_201_CREATED,
)
def create_multiplayer_room(
    body: RoomCreateIn,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    rooms: IMultiplayerRepository = Depends(get_multiplayer_repo),
) -> MultiplayerRoomOut:
    if prof.teacher_school_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas associé à un établissement",
        )
    school_students = school_repo.list_students(prof.teacher_school_id)
    group_students = [
        s for s in school_students if _student_group_key(s) == body.classLevel
    ]
    if not group_students:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun élève trouvé pour ce groupe",
        )
    allowed_ids = {s.id for s in group_students}
    if not all(participant_id in allowed_ids for participant_id in body.participantIds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un ou plusieurs élèves sélectionnés n'appartiennent pas à ce groupe",
        )
    selected_students = [s for s in group_students if s.id in set(body.participantIds)]
    room_code = secrets.token_hex(_ROOM_CODE_BYTES).upper()
    room = rooms.create(
        room_code=room_code,
        label=body.label,
        professor_id=prof.id,
        school_id=prof.teacher_school_id,
        data=_build_room_data(body.classLevel, selected_students),
        class_level=body.classLevel,
    )
    db.commit()
    return MultiplayerRoomOut.from_domain(room)


@router.get("/lessons", response_model=list[LessonOut])
def list_lessons(
    prof: User = Depends(require_prof),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> list[LessonOut]:
    return [LessonOut.from_domain(x) for x in lessons.list_by_professor(prof.id)]


@router.post("/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_lesson(
    body: LessonCreateIn,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> LessonOut:
    lesson = lessons.create(
        title=body.title,
        content=body.content,
        category=body.category,
        level=body.level,
        sort_order=body.sortOrder,
        professor_id=prof.id,
        school_id=prof.teacher_school_id,
        visibility=_normalize_visibility(body.visibility, prof),
    )
    db.commit()
    return LessonOut.from_domain(lesson)


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(
    lesson_id: UUID,
    body: LessonCreateIn,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> LessonOut:
    existing = lessons.get(lesson_id)
    if existing is None or existing.professor_id != prof.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leçon introuvable",
        )
    updated = lessons.update(
        lesson_id,
        title=body.title,
        content=body.content,
        category=body.category,
        level=body.level,
        sort_order=body.sortOrder,
        school_id=prof.teacher_school_id,
        visibility=_normalize_visibility(body.visibility, prof),
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leçon introuvable")
    db.commit()


@router.get("/quiz-questions", response_model=list[QuizQuestionOut])
def list_quiz_questions(
    prof: User = Depends(require_prof),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> list[QuizQuestionOut]:
    return [QuizQuestionOut.from_domain(x) for x in quizzes.list_by_professor(prof.id)]


@router.post(
    "/quiz-questions",
    response_model=QuizQuestionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz_question(
    body: QuizQuestionCreateIn,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> QuizQuestionOut:
    if body.correctIndex < 0 or body.correctIndex >= len(body.options):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correctIndex out of range",
        )
    question = quizzes.create(
        question=body.question,
        options=body.options,
        correct_index=body.correctIndex,
        explanation=body.explanation,
        category=body.category,
        level=body.level,
        professor_id=prof.id,
        school_id=prof.teacher_school_id,
        visibility=_normalize_visibility(body.visibility, prof),
    )
    db.commit()
    return QuizQuestionOut.from_domain(question)


@router.put("/quiz-questions/{question_id}", response_model=QuizQuestionOut)
def update_quiz_question(
    question_id: UUID,
    body: QuizQuestionUpdateIn,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> QuizQuestionOut:
    current = quizzes.get(question_id)
    if current is None or current.professor_id != prof.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question introuvable",
        )
    options = body.options if body.options is not None else current.options
    correct_index = (
        body.correctIndex if body.correctIndex is not None else current.correct_index
    )
    if correct_index < 0 or correct_index >= len(options):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correctIndex out of range",
        )
    updated = quizzes.update(
        question_id,
        question=body.question,
        options=body.options,
        correct_index=body.correctIndex,
        explanation=body.explanation,
        category=body.category,
        level=body.level,
        visibility=_normalize_visibility(body.visibility, prof)
        if body.visibility is not None
        else None,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question introuvable",
        )
    db.commit()
    return QuizQuestionOut.from_domain(updated)


@router.delete("/quiz-questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz_question(
    question_id: UUID,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    quizzes: IQuizRepository = Depends(get_quiz_repo),
) -> None:
    current = quizzes.get(question_id)
    if current is None or current.professor_id != prof.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question introuvable",
        )
    if not quizzes.delete(question_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question introuvable",
        )
    db.commit()


@router.get("/stories", response_model=list[StoryOut])
def list_stories(
    prof: User = Depends(require_prof),
    stories: IStoryRepository = Depends(get_story_repo),
) -> list[StoryOut]:
    return [StoryOut.from_domain(x) for x in stories.list_by_professor(prof.id)]


@router.post("/stories", response_model=StoryOut, status_code=status.HTTP_201_CREATED)
def create_story(
    body: StoryCreateIn,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    stories: IStoryRepository = Depends(get_story_repo),
) -> StoryOut:
    story = stories.create(
        title=body.title,
        content=body.content,
        level=body.level,
        audio_url=body.audioUrl,
        professor_id=prof.id,
        school_id=prof.teacher_school_id,
        visibility=_normalize_visibility(body.visibility, prof),
    )
    db.commit()
    return StoryOut.from_domain(story)


@router.put("/stories/{story_id}", response_model=StoryOut)
def update_story(
    story_id: UUID,
    body: StoryUpdateIn,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    stories: IStoryRepository = Depends(get_story_repo),
) -> StoryOut:
    current = stories.get(story_id)
    if current is None or current.professor_id != prof.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Histoire introuvable",
        )
    updated = stories.update(
        story_id,
        title=body.title,
        content=body.content,
        level=body.level,
        audio_url=body.audioUrl,
        visibility=_normalize_visibility(body.visibility, prof)
        if body.visibility is not None
        else None,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Histoire introuvable",
        )
    db.commit()
    return StoryOut.from_domain(updated)


@router.delete("/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_story(
    story_id: UUID,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    stories: IStoryRepository = Depends(get_story_repo),
) -> None:
    current = stories.get(story_id)
    if current is None or current.professor_id != prof.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Histoire introuvable",
        )
    if not stories.delete(story_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Histoire introuvable",
        )
    db.commit()
    return LessonOut.from_domain(updated)


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: UUID,
    db: Session = Depends(get_db),
    prof: User = Depends(require_prof),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> None:
    existing = lessons.get(lesson_id)
    if existing is None or existing.professor_id != prof.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leçon introuvable",
        )
    if not lessons.delete(lesson_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leçon introuvable")
    db.commit()
