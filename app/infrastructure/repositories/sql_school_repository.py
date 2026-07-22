from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import School, SchoolWithHash, User
from app.domain.ports import ISchoolRepository
from app.infrastructure.models.school import SchoolORM
from app.infrastructure.models.user import UserORM


class SqlSchoolRepository(ISchoolRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        created_by_admin_id: UUID,
        address: str | None,
        city: str | None,
        postal_code: str | None,
        phone: str | None,
        director_name: str | None,
        must_change_password: bool = False,
        logo_url: str | None = None,
    ) -> School:
        row = SchoolORM(
            name=name,
            email=email.lower().strip(),
            password_hash=password_hash,
            created_by_admin_id=created_by_admin_id,
            address=address,
            city=city,
            postal_code=postal_code,
            phone=phone,
            director_name=director_name,
            logo_url=logo_url,
            is_active=True,
            must_change_password=must_change_password,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def change_password(self, school_id: UUID, password_hash: str) -> None:
        from sqlalchemy import update
        stmt = (
            update(SchoolORM)
            .where(SchoolORM.id == school_id)
            .values(password_hash=password_hash, must_change_password=False)
        )
        self._session.execute(stmt)
        self._session.flush()

    def get_by_id(self, school_id: UUID) -> School | None:
        row = self._session.get(SchoolORM, school_id)
        return _to_domain(row) if row else None

    def get_by_email(self, email: str) -> SchoolWithHash | None:
        stmt = select(SchoolORM).where(SchoolORM.email == email.lower().strip())
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return SchoolWithHash(school=_to_domain(row), password_hash=row.password_hash)

    def list_all(self) -> list[School]:
        stmt = select(SchoolORM).order_by(SchoolORM.created_at.desc())
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def update(
        self,
        school_id: UUID,
        *,
        name: str | None = None,
        address: str | None = None,
        city: str | None = None,
        postal_code: str | None = None,
        phone: str | None = None,
        director_name: str | None = None,
        is_active: bool | None = None,
        logo_url: str | None = None,
        clear_logo_url: bool = False,
    ) -> School | None:
        row = self._session.get(SchoolORM, school_id)
        if row is None:
            return None
        if name is not None:
            row.name = name
        if address is not None:
            row.address = address
        if city is not None:
            row.city = city
        if postal_code is not None:
            row.postal_code = postal_code
        if phone is not None:
            row.phone = phone
        if director_name is not None:
            row.director_name = director_name
        if is_active is not None:
            row.is_active = is_active
        if clear_logo_url:
            row.logo_url = None
        elif logo_url is not None:
            row.logo_url = logo_url
        self._session.flush()
        return _to_domain(row)

    def delete(self, school_id: UUID) -> bool:
        row = self._session.get(SchoolORM, school_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def list_students(self, school_id: UUID) -> list[User]:
        stmt = (
            select(UserORM)
            .where(UserORM.school_id == school_id)
            .order_by(UserORM.last_name, UserORM.first_name)
        )
        return [_to_user(r) for r in self._session.scalars(stmt).all()]

    def list_professors(self, school_id: UUID) -> list[User]:
        stmt = (
            select(UserORM)
            .where(UserORM.teacher_school_id == school_id)
            .order_by(UserORM.last_name, UserORM.first_name)
        )
        return [_to_user(r) for r in self._session.scalars(stmt).all()]

    def count(self) -> int:
        from sqlalchemy import func
        return int(
            self._session.scalar(select(func.count()).select_from(SchoolORM)) or 0
        )


def _to_domain(row: SchoolORM) -> School:
    return School(
        id=row.id,
        name=row.name,
        email=row.email,
        is_active=row.is_active,
        must_change_password=row.must_change_password,
        created_at=row.created_at,
        address=row.address,
        city=row.city,
        postal_code=row.postal_code,
        phone=row.phone,
        director_name=row.director_name,
        created_by_admin_id=row.created_by_admin_id,
        logo_url=row.logo_url,
    )


def _to_user(row: UserORM) -> User:
    return User(
        id=row.id,
        email=row.email,
        first_name=row.first_name,
        last_name=row.last_name,
        level=row.level,
        created_at=row.created_at,
        role=row.role,
        is_active=row.is_active,
        must_change_password=row.must_change_password,
        class_level=row.class_level,
        school_id=row.school_id,
        teacher_school_id=row.teacher_school_id,
        phone=row.phone,
        date_of_birth=row.date_of_birth,
        assigned_learning_path_id=row.assigned_learning_path_id,
        profile_picture_url=row.profile_picture_url,
    )
