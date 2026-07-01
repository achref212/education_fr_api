from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.entities import PasswordResetCode
from app.domain.ports import IPasswordResetRepository
from app.infrastructure.models.password_reset_code import PasswordResetCodeORM


class SqlPasswordResetRepository(IPasswordResetRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        user_id: UUID,
        code_hash: str,
        expires_at: datetime,
    ) -> PasswordResetCode:
        row = PasswordResetCodeORM(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expires_at,
            used=False,
            attempts=0,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def get_latest_for_user(self, user_id: UUID) -> PasswordResetCode | None:
        stmt = (
            select(PasswordResetCodeORM)
            .where(PasswordResetCodeORM.user_id == user_id)
            .order_by(PasswordResetCodeORM.created_at.desc())
            .limit(1)
        )
        row = self._session.scalars(stmt).first()
        return _to_domain(row) if row else None

    def get_by_id(self, code_id: UUID) -> PasswordResetCode | None:
        row = self._session.get(PasswordResetCodeORM, code_id)
        return _to_domain(row) if row else None

    def increment_attempts(self, code_id: UUID) -> None:
        stmt = (
            update(PasswordResetCodeORM)
            .where(PasswordResetCodeORM.id == code_id)
            .values(attempts=PasswordResetCodeORM.attempts + 1)
        )
        self._session.execute(stmt)

    def mark_used(self, code_id: UUID) -> None:
        stmt = (
            update(PasswordResetCodeORM)
            .where(PasswordResetCodeORM.id == code_id)
            .values(used=True)
        )
        self._session.execute(stmt)

    def invalidate_all_for_user(self, user_id: UUID) -> None:
        stmt = (
            update(PasswordResetCodeORM)
            .where(PasswordResetCodeORM.user_id == user_id)
            .values(used=True)
        )
        self._session.execute(stmt)


def _to_domain(row: PasswordResetCodeORM) -> PasswordResetCode:
    return PasswordResetCode(
        id=row.id,
        user_id=row.user_id,
        code_hash=row.code_hash,
        expires_at=row.expires_at,
        used=row.used,
        attempts=row.attempts,
        created_at=row.created_at,
    )
