from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import User
from app.domain.ports import IAdminUserRepository
from app.infrastructure.models.user import UserORM


class SqlAdminUserRepository(IAdminUserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_user_with_role(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        level: str,
        role: str,
    ) -> User:
        row = UserORM(
            email=email.lower().strip(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            level=level,
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        self._session.flush()
        return _to_user(row)

    def list_users(self) -> list[User]:
        stmt = select(UserORM).order_by(UserORM.created_at.desc())
        rows = self._session.scalars(stmt).all()
        return [_to_user(r) for r in rows]

    def count_users(self) -> int:
        return int(
            self._session.scalar(select(func.count()).select_from(UserORM)) or 0
        )

    def count_active_users(self) -> int:
        return int(
            self._session.scalar(
                select(func.count()).select_from(UserORM).where(UserORM.is_active)
            )
            or 0
        )

    def count_by_level(self) -> dict[str, int]:
        rows = self._session.execute(
            select(UserORM.level, func.count())
            .group_by(UserORM.level)
        ).all()
        return {str(lev): int(c) for lev, c in rows}

    def count_admins(self) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(UserORM)
                .where(UserORM.role == "admin")
            )
            or 0
        )

    def update_user(
        self,
        user_id: UUID,
        *,
        role: str | None = None,
        level: str | None = None,
        is_active: bool | None = None,
    ) -> User | None:
        row = self._session.get(UserORM, user_id)
        if row is None:
            return None
        if role is not None:
            row.role = role
        if level is not None:
            row.level = level
        if is_active is not None:
            row.is_active = is_active
        # bump updated: users table has no updated_at, flush is enough
        self._session.flush()
        return _to_user(row)

    def delete_user(self, user_id: UUID) -> bool:
        row = self._session.get(UserORM, user_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True


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
    )
