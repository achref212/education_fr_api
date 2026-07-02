import secrets
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import MultiplayerRoom
from app.domain.ports import IMultiplayerRepository
from app.infrastructure.models.multiplayer_room import MultiplayerRoomORM


class SqlMultiplayerRepository(IMultiplayerRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[MultiplayerRoom]:
        stmt = select(MultiplayerRoomORM).order_by(
            MultiplayerRoomORM.updated_at.desc()
        )
        rows = self._session.scalars(stmt).all()
        return [_to_domain(r) for r in rows]

    def list_by_professor(self, professor_id: UUID) -> list[MultiplayerRoom]:
        stmt = (
            select(MultiplayerRoomORM)
            .where(MultiplayerRoomORM.professor_id == professor_id)
            .order_by(MultiplayerRoomORM.created_at.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def create(
        self,
        room_code: str,
        label: str | None,
        professor_id: UUID,
        school_id: UUID | None,
    ) -> MultiplayerRoom:
        now = datetime.now(timezone.utc)
        row = MultiplayerRoomORM(
            id=uuid.uuid4(),
            room_code=room_code,
            data={},
            label=label,
            professor_id=professor_id,
            school_id=school_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def count(self) -> int:
        return int(
            self._session.scalar(
                select(func.count()).select_from(MultiplayerRoomORM)
            )
            or 0
        )


def _to_domain(row: MultiplayerRoomORM) -> MultiplayerRoom:
    return MultiplayerRoom(
        id=row.id,
        room_code=row.room_code,
        data=dict(row.data) if row.data else {},
        label=row.label,
        created_at=row.created_at,
        updated_at=row.updated_at,
        professor_id=row.professor_id,
        school_id=row.school_id,
    )
