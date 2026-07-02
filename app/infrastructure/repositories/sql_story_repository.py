import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import Story
from app.domain.ports import IStoryRepository
from app.infrastructure.models.story import StoryORM


class SqlStoryRepository(IStoryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Story]:
        stmt = select(StoryORM).order_by(StoryORM.created_at.desc())
        rows = self._session.scalars(stmt).all()
        return [_to_domain(r) for r in rows]

    def list_by_level(self, level: str) -> list[Story]:
        stmt = (
            select(StoryORM)
            .where(StoryORM.level == level)
            .order_by(StoryORM.created_at.desc())
        )
        return [_to_domain(r) for r in self._session.scalars(stmt).all()]

    def get(self, story_id: UUID) -> Story | None:
        row = self._session.get(StoryORM, story_id)
        return _to_domain(row) if row else None

    def create(
        self,
        title: str,
        content: str,
        level: str,
        audio_url: str | None,
    ) -> Story:
        now = datetime.now(timezone.utc)
        row = StoryORM(
            id=uuid.uuid4(),
            title=title,
            content=content,
            level=level,
            audio_url=audio_url,
            created_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def update(
        self,
        story_id: UUID,
        *,
        title: str | None = None,
        content: str | None = None,
        level: str | None = None,
        audio_url: str | None = None,
    ) -> Story | None:
        row = self._session.get(StoryORM, story_id)
        if row is None:
            return None
        if title is not None:
            row.title = title
        if content is not None:
            row.content = content
        if level is not None:
            row.level = level
        if audio_url is not None:
            row.audio_url = audio_url
        self._session.flush()
        return _to_domain(row)

    def delete(self, story_id: UUID) -> bool:
        row = self._session.get(StoryORM, story_id)
        if row is None:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    def count(self) -> int:
        return int(
            self._session.scalar(select(func.count()).select_from(StoryORM)) or 0
        )


def _to_domain(row: StoryORM) -> Story:
    return Story(
        id=row.id,
        title=row.title,
        content=row.content,
        level=row.level,
        audio_url=row.audio_url,
        created_at=row.created_at,
    )
