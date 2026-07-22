from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import MediaAsset
from app.domain.ports import IMediaAssetRepository
from app.infrastructure.models.media_asset import MediaAssetORM


class SqlMediaAssetRepository(IMediaAssetRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        owner_type: str | None,
        owner_id: UUID | None,
        asset_type: str,
        title: str | None,
        url: str,
        storage_path: str | None,
        mime_type: str | None,
        size_bytes: int | None,
        metadata: dict | None = None,
    ) -> MediaAsset:
        now = datetime.now(timezone.utc)
        row = MediaAssetORM(
            owner_type=owner_type,
            owner_id=owner_id,
            asset_type=asset_type,
            title=title,
            url=url,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            meta=metadata or {},
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        return _to_domain(row)

    def list_all(
        self,
        *,
        owner_type: str | None = None,
        owner_id: UUID | None = None,
        asset_type: str | None = None,
        is_active: bool | None = True,
    ) -> list[MediaAsset]:
        stmt = select(MediaAssetORM).order_by(MediaAssetORM.created_at.desc())
        if owner_type is not None:
            stmt = stmt.where(MediaAssetORM.owner_type == owner_type)
        if owner_id is not None:
            stmt = stmt.where(MediaAssetORM.owner_id == owner_id)
        if asset_type is not None:
            stmt = stmt.where(MediaAssetORM.asset_type == asset_type)
        if is_active is not None:
            stmt = stmt.where(MediaAssetORM.is_active == is_active)
        return [_to_domain(row) for row in self._session.scalars(stmt).all()]

    def archive(self, asset_id: UUID) -> MediaAsset | None:
        row = self._session.get(MediaAssetORM, asset_id)
        if row is None:
            return None
        row.is_active = False
        row.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        return _to_domain(row)


def _to_domain(row: MediaAssetORM) -> MediaAsset:
    return MediaAsset(
        id=row.id,
        owner_type=row.owner_type,
        owner_id=row.owner_id,
        asset_type=row.asset_type,
        title=row.title,
        url=row.url,
        storage_path=row.storage_path,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        metadata=row.meta,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
