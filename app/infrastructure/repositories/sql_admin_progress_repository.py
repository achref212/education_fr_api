from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import ProgressData, UserProgressRow
from app.domain.ports import IAdminProgressRepository
from app.infrastructure.models.user import UserORM
from app.infrastructure.models.user_progress import UserProgressORM
from app.infrastructure.repositories.sql_admin_user_repository import _to_user


class SqlAdminProgressRepository(IAdminProgressRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all_with_users(self) -> list[UserProgressRow]:
        stmt = (
            select(UserORM, UserProgressORM)
            .select_from(UserORM)
            .outerjoin(UserProgressORM, UserORM.id == UserProgressORM.user_id)
        )
        rows = self._session.execute(stmt).all()
        out: list[UserProgressRow] = []
        for urow, prow in rows:
            user = _to_user(urow)
            if prow is not None and prow.data:
                progress = ProgressData.from_dict(_normalize_progress_keys(prow.data))
            else:
                progress = ProgressData.empty()
            out.append(UserProgressRow(user=user, progress=progress))
        return out


def _normalize_progress_keys(d: dict[str, Any]) -> dict[str, Any]:
    """Accept either camelCase (client) or snake internal keys."""
    if "lessonsCompleted" in d or "quizScores" in d:
        return d
    return {
        "lessonsCompleted": d.get("lessons_completed", []),
        "quizScores": d.get("quiz_scores", {}),
        "exerciseScores": d.get("exercise_scores", {}),
    }
