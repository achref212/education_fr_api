import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_lesson_repo,
    get_multiplayer_repo,
    get_progress_repo,
    get_recommendation_repo,
    get_school_repo,
    require_prof,
)
from app.api.schemas.admin import LessonCreateIn, LessonOut, MultiplayerRoomOut
from app.api.schemas.recommendation import RecommendationCreate, RecommendationOut
from app.api.schemas.user import UserOut
from app.domain.entities import User
from app.domain.ports import (
    ILessonRepository,
    IMultiplayerRepository,
    IProgressRepository,
    IRecommendationRepository,
    ISchoolRepository,
)
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/prof", tags=["professor"])

_ROOM_CODE_BYTES = 4


class RoomCreateIn(BaseModel):
    label: str | None = Field(default=None, max_length=255)


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
    rooms: IMultiplayerRepository = Depends(get_multiplayer_repo),
) -> MultiplayerRoomOut:
    room_code = secrets.token_hex(_ROOM_CODE_BYTES).upper()
    room = rooms.create(
        room_code=room_code,
        label=body.label,
        professor_id=prof.id,
        school_id=prof.teacher_school_id,
    )
    db.commit()
    return MultiplayerRoomOut.from_domain(room)


@router.get("/lessons", response_model=list[LessonOut])
def list_lessons(
    prof: User = Depends(require_prof),
    lessons: ILessonRepository = Depends(get_lesson_repo),
) -> list[LessonOut]:
    return [LessonOut.from_domain(x) for x in lessons.list_all()]


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
    )
    db.commit()
    return LessonOut.from_domain(lesson)
