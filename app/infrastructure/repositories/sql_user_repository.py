from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
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
    ) -> User:
        row = UserORM(
            email=email.lower().strip(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            level=level,
            role="user",
            is_active=True,
            created_at=datetime.now(timezone.utc),
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
    )
