from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_delf_test_service, get_user_repo, require_student
from app.api.schemas.delf_test import (
    DelfTestHistoryOut,
    DelfTestResultsOut,
    DelfTestSectionSubmitIn,
    DelfTestSectionSubmitOut,
    DelfTestStartOut,
)
from app.application.delf_test_service import DelfTestError, DelfTestService
from app.domain.entities import User
from app.domain.ports import IUserRepository
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/delf-tests", tags=["delf-tests"])


def _handle_error(exc: DelfTestError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)


@router.post("/start", response_model=DelfTestStartOut)
def start_delf_test(
    user: User = Depends(require_student),
    service: DelfTestService = Depends(get_delf_test_service),
    db: Session = Depends(get_db),
) -> DelfTestStartOut:
    try:
        result = service.start_test(user)
        db.commit()
        return DelfTestStartOut.model_validate(result)
    except DelfTestError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.get("/me/active", response_model=DelfTestStartOut | None)
def get_active_delf_test(
    user: User = Depends(require_student),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestStartOut | None:
    result = service.get_active_test(user)
    if result is None:
        return None
    return DelfTestStartOut.model_validate(result)


@router.get("/me/history", response_model=list[DelfTestHistoryOut])
def list_my_delf_test_history(
    user: User = Depends(require_student),
    service: DelfTestService = Depends(get_delf_test_service),
) -> list[DelfTestHistoryOut]:
    items = service.list_history(user)
    return [DelfTestHistoryOut.model_validate(item) for item in items]


@router.get("/{session_id}", response_model=DelfTestStartOut)
def get_delf_test_session(
    session_id: UUID,
    user: User = Depends(require_student),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestStartOut:
    try:
        result = service.get_session(user, session_id)
        return DelfTestStartOut.model_validate(result)
    except DelfTestError as exc:
        raise _handle_error(exc) from exc


@router.post(
    "/{session_id}/sections/{category}/submit",
    response_model=DelfTestSectionSubmitOut,
)
def submit_delf_test_section(
    session_id: UUID,
    category: str,
    body: DelfTestSectionSubmitIn,
    user: User = Depends(require_student),
    service: DelfTestService = Depends(get_delf_test_service),
    db: Session = Depends(get_db),
) -> DelfTestSectionSubmitOut:
    try:
        answers = [a.model_dump(by_alias=True) for a in body.answers]
        result = service.submit_section(user, session_id, category, answers)
        db.commit()
        return DelfTestSectionSubmitOut.model_validate(result)
    except DelfTestError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.post("/{session_id}/finish", response_model=DelfTestResultsOut)
def finish_delf_test(
    session_id: UUID,
    user: User = Depends(require_student),
    service: DelfTestService = Depends(get_delf_test_service),
    db: Session = Depends(get_db),
) -> DelfTestResultsOut:
    try:
        result = service.finish_test(user, session_id)
        db.commit()
        return DelfTestResultsOut.model_validate(result)
    except DelfTestError as exc:
        db.rollback()
        raise _handle_error(exc) from exc


@router.get("/{session_id}/results", response_model=DelfTestResultsOut)
def get_delf_test_results(
    session_id: UUID,
    user: User = Depends(require_student),
    service: DelfTestService = Depends(get_delf_test_service),
) -> DelfTestResultsOut:
    try:
        result = service.get_results(user, session_id)
        return DelfTestResultsOut.model_validate(result)
    except DelfTestError as exc:
        raise _handle_error(exc) from exc
