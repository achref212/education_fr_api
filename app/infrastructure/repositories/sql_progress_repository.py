from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import ProgressData
from app.domain.ports import IProgressRepository
from app.infrastructure.models.user_progress import UserProgressORM


class SqlProgressRepository(IProgressRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_user(self, user_id: UUID) -> ProgressData:
        stmt = select(UserProgressORM).where(UserProgressORM.user_id == user_id)
        row = self._session.scalars(stmt).first()
        if row is None or not row.data:
            return ProgressData.empty()
        return ProgressData.from_dict(row.data)

    def upsert_for_user(self, user_id: UUID, data: ProgressData) -> None:
        stmt = select(UserProgressORM).where(UserProgressORM.user_id == user_id)
        row = self._session.scalars(stmt).first()
        payload = data.to_dict()
        if row is None:
            self._session.add(
                UserProgressORM(user_id=user_id, data=payload),
            )
        else:
            row.data = payload
        self._session.flush()
