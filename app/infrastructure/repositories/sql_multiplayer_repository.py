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
    )
