from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_parcours_service,
    require_student,
)
from app.api.schemas.parcours import (
    DifficultyUpdateIn,
    ParcoursOut,
    ParcoursStepOut,
    ParcoursSummaryOut,
    StepCompleteIn,
    StepCompleteOut,
)
from app.application.parcours_service import ParcoursError, ParcoursService
from app.domain.entities import User
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/parcours", tags=["parcours"])


def _build_parcours_out(data: dict) -> ParcoursOut:
    path = data["path"]
    steps = data["steps"]
    stats = data["stats"]
    total_steps = len(steps)
    completed_steps = sum(1 for s in steps if s["status"] == "completed")
    completion_percent = (
        round(completed_steps / total_steps * 100, 1) if total_steps else 0.0
    )
    step_outs = [
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
    ]
    return ParcoursOut(
        pathId=path.id,
        title=path.title,
        description=path.description,
        classLevel=path.class_level,
        delfTargetLevel=path.delf_target_level,
        totalXp=stats.total_xp,
        currentStreak=stats.current_streak,
        preferredDifficulty=stats.preferred_difficulty,
        completionPercent=completion_percent,
        steps=step_outs,
    )


@router.get("/me", response_model=ParcoursOut)
def get_my_parcours(
    user: User = Depends(require_student),
    svc: ParcoursService = Depends(get_parcours_service),
) -> ParcoursOut:
    try:
        data = svc.get_parcours_for_user(user)
    except ParcoursError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
    return _build_parcours_out(data)


@router.get("/me/summary", response_model=ParcoursSummaryOut)
def get_my_parcours_summary(
    user: User = Depends(require_student),
    svc: ParcoursService = Depends(get_parcours_service),
) -> ParcoursSummaryOut:
    try:
        summary = svc.get_summary(user)
    except ParcoursError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
    return ParcoursSummaryOut(
        classLevel=summary.class_level,
        delfTargetLevel=summary.delf_target_level,
        completionPercent=summary.completion_percent,
        totalSteps=summary.total_steps,
        completedSteps=summary.completed_steps,
        totalXp=summary.total_xp,
        currentStreak=summary.current_streak,
        preferredDifficulty=summary.preferred_difficulty,
        nextStepId=summary.next_step_id,
        nextStepTitle=summary.next_step_title,
    )


@router.post("/steps/{step_id}/start", status_code=status.HTTP_204_NO_CONTENT)
def start_step(
    step_id: UUID,
    user: User = Depends(require_student),
    svc: ParcoursService = Depends(get_parcours_service),
) -> None:
    try:
        svc.start_step(user, step_id)
    except ParcoursError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc


@router.post("/steps/{step_id}/complete", response_model=StepCompleteOut)
def complete_step(
    step_id: UUID,
    body: StepCompleteIn,
    user: User = Depends(require_student),
    svc: ParcoursService = Depends(get_parcours_service),
) -> StepCompleteOut:
    try:
        result = svc.complete_step(user, step_id, body.score)
    except ParcoursError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    return StepCompleteOut(
        stepId=step_id,
        score=result["score"],
        xpEarned=result["xpEarned"],
        passed=result["passed"],
        nextStepId=result["nextStepId"],
        parcoursPercent=result["parcoursPercent"],
    )


@router.put("/me/difficulty")
def update_difficulty(
    body: DifficultyUpdateIn,
    user: User = Depends(require_student),
    svc: ParcoursService = Depends(get_parcours_service),
) -> dict:
    return svc.set_difficulty(user, body.difficulty)
