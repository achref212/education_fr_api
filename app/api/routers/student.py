from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_student_delf_mock_exam_service,
    get_student_service,
    require_student,
)
from app.api.schemas.delf_mock_exam import DelfMockExamOut
from app.api.schemas.student import (
    StudentDelfMockAttemptOut,
    StudentDelfMockAttemptSubmitIn,
    StudentAchievementsOut,
    StudentHintOut,
    StudentHubOut,
    StudentLeaderboardOut,
    StudentReviewItemOut,
    StudentReviewOut,
)
from app.application.student_delf_mock_exam_service import (
    StudentDelfMockExamError,
    StudentDelfMockExamService,
)
from app.application.student_service import StudentError, StudentService
from app.domain.entities import User
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/student/me", tags=["student"])


@router.get("/hub", response_model=StudentHubOut)
def get_my_student_hub(
    user: User = Depends(require_student),
    service: StudentService = Depends(get_student_service),
) -> StudentHubOut:
    return StudentHubOut.model_validate(service.get_hub(user))


@router.get("/leaderboard", response_model=StudentLeaderboardOut)
def get_my_student_leaderboard(
    scope: str = Query("class", pattern="^(class|school)$"),
    user: User = Depends(require_student),
    service: StudentService = Depends(get_student_service),
) -> StudentLeaderboardOut:
    return StudentLeaderboardOut.model_validate(service.get_leaderboard(user, scope))


@router.get("/achievements", response_model=StudentAchievementsOut)
def get_my_student_achievements(
    user: User = Depends(require_student),
    service: StudentService = Depends(get_student_service),
) -> StudentAchievementsOut:
    return StudentAchievementsOut.model_validate(service.get_achievements(user))


@router.get("/review", response_model=StudentReviewOut)
def get_my_student_review(
    user: User = Depends(require_student),
    service: StudentService = Depends(get_student_service),
) -> StudentReviewOut:
    return StudentReviewOut.model_validate(service.get_review(user))


@router.post("/review/{item_id}/complete", response_model=StudentReviewItemOut)
def complete_my_student_review_item(
    item_id: UUID,
    user: User = Depends(require_student),
    service: StudentService = Depends(get_student_service),
    db: Session = Depends(get_db),
) -> StudentReviewItemOut:
    try:
        result = service.complete_review_item(user, item_id)
        db.commit()
        return StudentReviewItemOut.model_validate(result)
    except StudentError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post("/review/{item_id}/hint", response_model=StudentHintOut)
def get_my_student_review_hint(
    item_id: UUID,
    user: User = Depends(require_student),
    service: StudentService = Depends(get_student_service),
) -> StudentHintOut:
    try:
        return StudentHintOut.model_validate(service.get_hint(user, item_id))
    except StudentError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


def _mock_exam_error(exc: StudentDelfMockExamError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=exc.message,
    )


@router.get("/delf-mock-exams", response_model=list[DelfMockExamOut])
def list_my_delf_mock_exams(
    user: User = Depends(require_student),
    service: StudentDelfMockExamService = Depends(
        get_student_delf_mock_exam_service
    ),
) -> list[DelfMockExamOut]:
    return [
        DelfMockExamOut.model_validate(item)
        for item in service.list_published_exams(user)
    ]


@router.get("/delf-mock-exams/{exam_id}", response_model=DelfMockExamOut)
def get_my_delf_mock_exam(
    exam_id: UUID,
    _user: User = Depends(require_student),
    service: StudentDelfMockExamService = Depends(
        get_student_delf_mock_exam_service
    ),
) -> DelfMockExamOut:
    try:
        return DelfMockExamOut.model_validate(service.get_published_exam(exam_id))
    except StudentDelfMockExamError as exc:
        raise _mock_exam_error(exc) from exc


@router.post(
    "/delf-mock-exams/{exam_id}/attempts",
    response_model=StudentDelfMockAttemptOut,
    status_code=status.HTTP_201_CREATED,
)
def create_my_delf_mock_attempt(
    exam_id: UUID,
    user: User = Depends(require_student),
    service: StudentDelfMockExamService = Depends(
        get_student_delf_mock_exam_service
    ),
    db: Session = Depends(get_db),
) -> StudentDelfMockAttemptOut:
    try:
        result = service.create_attempt(user, exam_id)
        db.commit()
        return StudentDelfMockAttemptOut.model_validate(result)
    except StudentDelfMockExamError as exc:
        db.rollback()
        raise _mock_exam_error(exc) from exc


@router.get(
    "/delf-mock-attempts/{attempt_id}",
    response_model=StudentDelfMockAttemptOut,
)
def get_my_delf_mock_attempt(
    attempt_id: UUID,
    user: User = Depends(require_student),
    service: StudentDelfMockExamService = Depends(
        get_student_delf_mock_exam_service
    ),
) -> StudentDelfMockAttemptOut:
    try:
        return StudentDelfMockAttemptOut.model_validate(
            service.get_attempt(user, attempt_id)
        )
    except StudentDelfMockExamError as exc:
        raise _mock_exam_error(exc) from exc


@router.post(
    "/delf-mock-attempts/{attempt_id}/submit",
    response_model=StudentDelfMockAttemptOut,
)
def submit_my_delf_mock_attempt(
    attempt_id: UUID,
    body: StudentDelfMockAttemptSubmitIn,
    user: User = Depends(require_student),
    service: StudentDelfMockExamService = Depends(
        get_student_delf_mock_exam_service
    ),
    db: Session = Depends(get_db),
) -> StudentDelfMockAttemptOut:
    try:
        answers = [answer.model_dump(by_alias=True) for answer in body.answers]
        result = service.submit_attempt(user, attempt_id, answers)
        db.commit()
        return StudentDelfMockAttemptOut.model_validate(result)
    except StudentDelfMockExamError as exc:
        db.rollback()
        raise _mock_exam_error(exc) from exc
