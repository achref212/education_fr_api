from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_progress_service
from app.api.schemas.progress import ProgressIn, ProgressOut
from app.application.progress_service import ProgressService
from app.domain.entities import ProgressData, User
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=ProgressOut)
def get_progress(
    user: User = Depends(get_current_user),
    svc: ProgressService = Depends(get_progress_service),
) -> ProgressOut:
    p = svc.get(user.id)
    d = p.to_dict()
    return ProgressOut(
        lessonsCompleted=d["lessonsCompleted"],
        quizScores=d["quizScores"],
        exerciseScores=d["exerciseScores"],
    )


@router.put("", status_code=status.HTTP_204_NO_CONTENT)
def put_progress(
    body: ProgressIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    svc: ProgressService = Depends(get_progress_service),
) -> None:
    data = ProgressData(
        lessons_completed=body.lessonsCompleted,
        quiz_scores=body.quizScores,
        exercise_scores=body.exerciseScores,
    )
    svc.put(user.id, data)
    db.commit()
