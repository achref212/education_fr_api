from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.entities import User, UserWithHash
from app.domain.ports import IUserRepository
from app.infrastructure.models.user import UserORM


class SqlUserRepository(IUserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        level: str,
        is_active: bool = False,
        phone: str | None = None,
        date_of_birth: date | None = None,
        class_level: str | None = None,
        school_id: str | None = None,
    ) -> User:
        row = UserORM(
            email=email.lower().strip(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            level=level,
            role="user",
            is_active=is_active,
            created_at=datetime.now(timezone.utc),
            phone=phone,
            date_of_birth=date_of_birth,
            class_level=class_level,
            school_id=school_id,
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain_user(row)

    def get_by_email(self, email: str) -> UserWithHash | None:
        stmt = select(UserORM).where(UserORM.email == email.lower().strip())
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return UserWithHash(
            user=_to_domain_user(row),
            password_hash=row.password_hash,
        )

    def get_by_id(self, user_id: UUID) -> User | None:
        row = self._session.get(UserORM, user_id)
        if row is None:
            return None
        return _to_domain_user(row)

    def change_password(self, user_id: UUID, password_hash: str) -> None:
        stmt = (
            update(UserORM)
            .where(UserORM.id == user_id)
            .values(password_hash=password_hash, must_change_password=False)
        )
        self._session.execute(stmt)
        self._session.flush()

    def update_password(self, user_id: UUID, password_hash: str) -> None:
        stmt = (
            update(UserORM)
            .where(UserORM.id == user_id)
            .values(password_hash=password_hash)
        )
        self._session.execute(stmt)

    def activate_user(self, user_id: UUID) -> None:
        stmt = (
            update(UserORM)
            .where(UserORM.id == user_id)
            .values(is_active=True)
        )
        self._session.execute(stmt)

    def update_profile(
        self,
        user_id: UUID,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        date_of_birth: date | None = None,
    ) -> User | None:
        row = self._session.get(UserORM, user_id)
        if row is None:
            return None
        if first_name is not None:
            row.first_name = first_name
        if last_name is not None:
            row.last_name = last_name
        if phone is not None:
            row.phone = phone
        if date_of_birth is not None:
            row.date_of_birth = date_of_birth
        self._session.flush()
        return _to_domain_user(row)

    def assign_learning_path(
        self, user_id: UUID, learning_path_id: UUID | None
    ) -> User | None:
        row = self._session.get(UserORM, user_id)
        if row is None:
            return None
        row.assigned_learning_path_id = learning_path_id
        self._session.flush()
        return _to_domain_user(row)


def _to_domain_user(row: UserORM) -> User:
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
    )
