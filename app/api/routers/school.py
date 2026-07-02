from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_auth_service,
    get_current_school,
    get_progress_repo,
    get_school_repo,
)
from app.api.schemas.school import ProfCreate, ProfCreateOut, SchoolOut
from app.api.schemas.user import UserOut
from app.api.schemas.admin import UserProgressItemOut
from app.application.auth_service import AuthError, AuthService
from app.domain.entities import School
from app.domain.ports import IProgressRepository, ISchoolRepository
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/school", tags=["school"])


@router.get("/me", response_model=SchoolOut)
def school_me(
    school: School = Depends(get_current_school),
) -> SchoolOut:
    return SchoolOut.from_domain(school)


@router.get("/students", response_model=list[UserOut])
def list_students(
    school: School = Depends(get_current_school),
    repo: ISchoolRepository = Depends(get_school_repo),
) -> list[UserOut]:
    students = repo.list_students(school.id)
    return [UserOut.from_domain(u) for u in students]


@router.get("/students/{student_id}", response_model=UserOut)
def get_student(
    student_id: UUID,
    school: School = Depends(get_current_school),
    repo: ISchoolRepository = Depends(get_school_repo),
) -> UserOut:
    students = repo.list_students(school.id)
    student = next((u for u in students if u.id == student_id), None)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Élève introuvable dans cet établissement",
        )
    return UserOut.from_domain(student)


@router.get("/students/{student_id}/progress")
def get_student_progress(
    student_id: UUID,
    school: School = Depends(get_current_school),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    progress_repo: IProgressRepository = Depends(get_progress_repo),
) -> dict:
    students = school_repo.list_students(school.id)
    student = next((u for u in students if u.id == student_id), None)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Élève introuvable dans cet établissement",
        )
    progress = progress_repo.get_for_user(student_id)
    return {
        "student": UserOut.from_domain(student).model_dump(),
        "progress": progress.to_dict(),
    }


@router.get("/professors", response_model=list[UserOut])
def list_professors(
    school: School = Depends(get_current_school),
    repo: ISchoolRepository = Depends(get_school_repo),
) -> list[UserOut]:
    profs = repo.list_professors(school.id)
    return [UserOut.from_domain(p) for p in profs]


@router.post("/professors", response_model=ProfCreateOut, status_code=status.HTTP_201_CREATED)
def create_professor(
    body: ProfCreate,
    db: Session = Depends(get_db),
    school: School = Depends(get_current_school),
    auth: AuthService = Depends(get_auth_service),
) -> ProfCreateOut:
    try:
        prof, plain_password = auth.create_prof_account(
            first_name=body.firstName,
            last_name=body.lastName,
            email=body.email,
            teacher_school_id=school.id,
            phone=body.phone,
            date_of_birth=body.dateOfBirth,
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
    return ProfCreateOut(
        userId=prof.id,
        firstName=prof.first_name,
        lastName=prof.last_name,
        email=prof.email,
        plainPassword=plain_password,
        phone=prof.phone,
        dateOfBirth=prof.date_of_birth,
    )
