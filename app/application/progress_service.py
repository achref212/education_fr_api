from uuid import UUID

from app.domain.entities import ProgressData
from app.domain.ports import IProgressRepository


class ProgressService:
    def __init__(self, progress: IProgressRepository) -> None:
        self._progress = progress

    def get(self, user_id: UUID) -> ProgressData:
        return self._progress.get_for_user(user_id)

    def put(self, user_id: UUID, data: ProgressData) -> None:
        self._progress.upsert_for_user(user_id, data)
