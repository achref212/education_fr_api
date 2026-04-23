import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import ContactMessage
from app.domain.ports import IContactRepository
from app.infrastructure.models.contact_message import ContactMessageORM


class SqlContactRepository(IContactRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[ContactMessage]:
        stmt = select(ContactMessageORM).order_by(ContactMessageORM.created_at.desc())
        rows = self._session.scalars(stmt).all()
        return [_to_domain(r) for r in rows]

    def get(self, message_id: UUID) -> ContactMessage | None:
        row = self._session.get(ContactMessageORM, message_id)
        return _to_domain(row) if row else None

    def mark_read(
        self, message_id: UUID, read: bool = True
    ) -> ContactMessage | None:
        row = self._session.get(ContactMessageORM, message_id)
        if row is None:
            return None
        row.read = read
        self._session.flush()
        return _to_domain(row)

    def delete(self, message_id: UUID) -> bool:
        row = self._session.get(ContactMessageORM, message_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def count_unread(self) -> int:
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(ContactMessageORM)
                .where(ContactMessageORM.read.is_(False))
            )
            or 0
        )


def _to_domain(row: ContactMessageORM) -> ContactMessage:
    return ContactMessage(
        id=row.id,
        name=row.name,
        email=row.email,
        subject=row.subject,
        message=row.message,
        created_at=row.created_at,
        read=row.read,
    )
