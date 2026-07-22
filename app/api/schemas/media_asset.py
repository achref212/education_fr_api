from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities import MediaAsset


class MediaAssetOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    ownerType: str | None = None
    ownerId: UUID | None = None
    assetType: str
    title: str | None = None
    url: str
    storagePath: str | None = None
    mimeType: str | None = None
    sizeBytes: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    isActive: bool
    createdAt: datetime
    updatedAt: datetime

    @classmethod
    def from_domain(cls, asset: MediaAsset) -> "MediaAssetOut":
        return cls(
            id=asset.id,
            ownerType=asset.owner_type,
            ownerId=asset.owner_id,
            assetType=asset.asset_type,
            title=asset.title,
            url=asset.url,
            storagePath=asset.storage_path,
            mimeType=asset.mime_type,
            sizeBytes=asset.size_bytes,
            metadata=asset.metadata,
            isActive=asset.is_active,
            createdAt=asset.created_at,
            updatedAt=asset.updated_at,
        )


class MediaAssetCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ownerType: str | None = None
    ownerId: UUID | None = None
    assetType: str
    title: str | None = None
    url: str
    metadata: dict[str, Any] = Field(default_factory=dict)
