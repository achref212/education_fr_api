from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_auth_service,
    get_current_school,
    get_delf_test_service,
    get_progress_repo,
    get_school_repo,
)
from app.api.schemas.delf_test import DelfTestHistoryOut
from app.application.delf_test_service import DelfTestService
from app.api.schemas.school import (
    ImportResultOut,
    ImportRowResultOut,
    ProfCreate,
    ProfCreateOut,
    SchoolOut,
    SchoolProfileUpdateIn,
)
from app.api.schemas.user import UserOut
from app.api.schemas.admin import UserProgressItemOut, AdminUserOut
from app.application.auth_service import AuthError, AuthService
from app.application.import_service import ImportParseError, parse_import_file, template_csv
from app.domain.entities import School
from app.domain.ports import IProgressRepository, ISchoolRepository
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/school", tags=["school"])


def _parse_import_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise AuthError(
            "invalid_date",
            "La date de naissance doit être au format AAAA-MM-JJ.",
        ) from exc


@router.get("/me", response_model=SchoolOut)
def school_me(
    school: School = Depends(get_current_school),
) -> SchoolOut:
    return SchoolOut.from_domain(school)


@router.patch("/me", response_model=SchoolOut)
def update_school_me(
    body: SchoolProfileUpdateIn,
    db: Session = Depends(get_db),
    school: School = Depends(get_current_school),
    auth: AuthService = Depends(get_auth_service),
) -> SchoolOut:
    try:
        updated = auth.update_school_profile(
            school,
            name=body.name,
            address=body.address,
            city=body.city,
            postal_code=body.postalCode,
            phone=body.phone,
            director_name=body.directorName,
            logo_url=body.logoUrl,
            clear_logo_url=("logoUrl" in body.model_fields_set and body.logoUrl is None),
        )
        db.commit()
    except AuthError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    return SchoolOut.from_domain(updated)


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


@router.get("/progress", response_model=list[UserProgressItemOut])
def list_students_progress(
    school: School = Depends(get_current_school),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    progress_repo: IProgressRepository = Depends(get_progress_repo),
) -> list[UserProgressItemOut]:
    students = school_repo.list_students(school.id)
    rows: list[UserProgressItemOut] = []
    for student in students:
        progress = progress_repo.get_for_user(student.id)
        rows.append(
            UserProgressItemOut(
                user=AdminUserOut.from_domain(student),
                progress=progress.to_dict(),
            )
        )
    return rows


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


@router.get("/students/{student_id}/delf-tests", response_model=list[DelfTestHistoryOut])
def get_student_delf_tests(
    student_id: UUID,
    school: School = Depends(get_current_school),
    school_repo: ISchoolRepository = Depends(get_school_repo),
    service: DelfTestService = Depends(get_delf_test_service),
) -> list[DelfTestHistoryOut]:
    students = school_repo.list_students(school.id)
    student = next((u for u in students if u.id == student_id), None)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Élève introuvable dans cet établissement",
        )
    items = service.list_student_history(student_id)
    return [DelfTestHistoryOut.model_validate(item) for item in items]


@router.get("/professors", response_model=list[UserOut])
def list_professors(
    school: School = Depends(get_current_school),
    repo: ISchoolRepository = Depends(get_school_repo),
) -> list[UserOut]:
    profs = repo.list_professors(school.id)
    return [UserOut.from_domain(p) for p in profs]


@router.get("/professors/import-template")
def professor_import_template(
    school: School = Depends(get_current_school),
) -> Response:
    return Response(
        content=template_csv("professors"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="modele-professeurs.csv"'},
    )


@router.post("/professors/import", response_model=ImportResultOut)
async def import_professors(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    school: School = Depends(get_current_school),
    auth: AuthService = Depends(get_auth_service),
) -> ImportResultOut:
    try:
        rows = await parse_import_file(file, kind="professors")
    except ImportParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc

    results: list[ImportRowResultOut] = []
    for row in rows:
        values = row.values
        first_name = values.get("firstName") or ""
        last_name = values.get("lastName") or ""
        email = values.get("email") or ""
        if not first_name or not last_name or not email:
            results.append(
                ImportRowResultOut(
                    rowNumber=row.row_number,
                    status="skipped",
                    email=email or None,
                    displayName=f"{first_name} {last_name}".strip() or None,
                    error="Prénom, nom et e-mail sont obligatoires.",
                )
            )
            continue
        try:
            birth_date = _parse_import_date(values.get("dateOfBirth") or None)
            prof, plain_password = auth.create_prof_account(
                first_name=first_name,
                last_name=last_name,
                email=email,
                teacher_school_id=school.id,
                phone=values.get("phone") or None,
                date_of_birth=birth_date,
            )
            db.commit()
            results.append(
                ImportRowResultOut(
                    rowNumber=row.row_number,
                    status="created",
                    email=prof.email,
                    displayName=f"{prof.first_name} {prof.last_name}",
                    createdId=prof.id,
                    plainPassword=plain_password,
                )
            )
        except AuthError as exc:
            db.rollback()
            results.append(
                ImportRowResultOut(
                    rowNumber=row.row_number,
                    status="skipped",
                    email=email,
                    displayName=f"{first_name} {last_name}".strip(),
                    error=exc.message,
                )
            )
        except IntegrityError:
            db.rollback()
            results.append(
                ImportRowResultOut(
                    rowNumber=row.row_number,
                    status="skipped",
                    email=email,
                    displayName=f"{first_name} {last_name}".strip(),
                    error="Cet e-mail est déjà utilisé.",
                )
            )
    created = sum(1 for result in results if result.status == "created")
    return ImportResultOut(
        totalRows=len(rows),
        createdCount=created,
        skippedCount=len(results) - created,
        results=results,
    )


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
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet e-mail est déjà utilisé",
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
