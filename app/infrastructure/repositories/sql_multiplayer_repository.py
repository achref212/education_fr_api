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

    def get_by_id(self, room_id: UUID) -> MultiplayerRoom | None:
        row = self._session.get(MultiplayerRoomORM, room_id)
        return _to_domain(row) if row else None

    def get_by_code(self, room_code: str) -> MultiplayerRoom | None:
        normalized = room_code.strip().upper()
        stmt = select(MultiplayerRoomORM).where(
            MultiplayerRoomORM.room_code == normalized
        )
        row = self._session.scalar(stmt)
        return _to_domain(row) if row else None

    def list_for_student(self, student_id: UUID) -> list[MultiplayerRoom]:
        student_key = str(student_id)
        rows = self._session.scalars(select(MultiplayerRoomORM)).all()
        result: list[MultiplayerRoom] = []
        for row in rows:
            data = row.data or {}
            participants = data.get("participants") or []
            player_ids = {p.get("id") for p in participants}
            if student_key in player_ids:
                result.append(_to_domain(row))
        return sorted(result, key=lambda r: r.updated_at, reverse=True)

    def create(
        self,
        room_code: str,
        label: str | None,
        professor_id: UUID,
        school_id: UUID | None,
        data: dict | None = None,
        class_level: str | None = None,
    ) -> MultiplayerRoom:
        now = datetime.now(timezone.utc)
        row = MultiplayerRoomORM(
            id=uuid.uuid4(),
            room_code=room_code,
            data=data or {},
            label=label,
            professor_id=professor_id,
            school_id=school_id,
            class_level=class_level,
            active_session_id=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def update_data(self, room_id: UUID, data: dict) -> MultiplayerRoom | None:
        row = self._session.get(MultiplayerRoomORM, room_id)
        if row is None:
            return None
        row.data = dict(data)
        row.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return _to_domain(row)

    def set_active_session(
        self, room_id: UUID, session_id: UUID | None
    ) -> MultiplayerRoom | None:
        row = self._session.get(MultiplayerRoomORM, room_id)
        if row is None:
            return None
        row.active_session_id = session_id
        row.updated_at = datetime.now(timezone.utc)
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
        class_level=row.class_level,
        active_session_id=row.active_session_id,
    )
