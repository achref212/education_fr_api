from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_account, get_media_asset_service, require_admin
from app.api.schemas.media_asset import MediaAssetCreateIn, MediaAssetOut
from app.application.media_asset_service import MediaAssetError, MediaAssetService
from app.domain.entities import School, User
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/admin/assets", tags=["admin-assets"])
account_router = APIRouter(prefix="/assets", tags=["assets"])


def _asset_error(exc: MediaAssetError) -> HTTPException:
    status_code = (
        status.HTTP_404_NOT_FOUND
        if exc.code == "not_found"
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(status_code=status_code, detail=exc.message)


@router.get("", response_model=list[MediaAssetOut])
def list_assets(
    owner_type: Annotated[str | None, Query(alias="ownerType")] = None,
    owner_id: Annotated[UUID | None, Query(alias="ownerId")] = None,
    asset_type: Annotated[str | None, Query(alias="assetType")] = None,
    is_active: Annotated[bool | None, Query(alias="isActive")] = True,
    _admin: User = Depends(require_admin),
    service: MediaAssetService = Depends(get_media_asset_service),
) -> list[MediaAssetOut]:
    try:
        assets = service.list_assets(
            owner_type=owner_type,
            owner_id=owner_id,
            asset_type=asset_type,
            is_active=is_active,
        )
    except MediaAssetError as exc:
        raise _asset_error(exc) from exc
    return [MediaAssetOut.from_domain(asset) for asset in assets]


@router.post("", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def register_asset_url(
    body: MediaAssetCreateIn,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    service: MediaAssetService = Depends(get_media_asset_service),
) -> MediaAssetOut:
    try:
        asset = service.register_url(
            owner_type=body.ownerType,
            owner_id=body.ownerId,
            asset_type=body.assetType,
            title=body.title,
            url=body.url,
            metadata=body.metadata,
        )
        db.commit()
    except MediaAssetError as exc:
        db.rollback()
        raise _asset_error(exc) from exc
    return MediaAssetOut.from_domain(asset)


@router.post("/upload", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def upload_asset(
    file: UploadFile = File(...),
    asset_type: str = Form(..., alias="assetType"),
    owner_type: str | None = Form(default=None, alias="ownerType"),
    owner_id: UUID | None = Form(default=None, alias="ownerId"),
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    service: MediaAssetService = Depends(get_media_asset_service),
) -> MediaAssetOut:
    try:
        asset = service.save_upload(
            file=file,
            owner_type=owner_type,
            owner_id=owner_id,
            asset_type=asset_type,
            title=title,
            metadata={"originalFilename": file.filename},
        )
        db.commit()
    except MediaAssetError as exc:
        db.rollback()
        raise _asset_error(exc) from exc
    return MediaAssetOut.from_domain(asset)


@router.delete("/{asset_id}", response_model=MediaAssetOut)
def archive_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    service: MediaAssetService = Depends(get_media_asset_service),
) -> MediaAssetOut:
    try:
        asset = service.archive(asset_id)
        db.commit()
    except MediaAssetError as exc:
        db.rollback()
        raise _asset_error(exc) from exc
    return MediaAssetOut.from_domain(asset)


@account_router.post("/profile-upload", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED)
def upload_current_account_profile_asset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    account: User | School = Depends(get_current_account),
    service: MediaAssetService = Depends(get_media_asset_service),
) -> MediaAssetOut:
    if isinstance(account, School):
        owner_type = "school"
        owner_id = account.id
        asset_type = "school_logo"
        title = f"Logo {account.name}"
    else:
        owner_type = "user"
        owner_id = account.id
        asset_type = "profile_image"
        title = f"Photo {account.first_name} {account.last_name}"
    try:
        asset = service.save_upload(
            file=file,
            owner_type=owner_type,
            owner_id=owner_id,
            asset_type=asset_type,
            title=title,
            metadata={"originalFilename": file.filename},
        )
        db.commit()
    except MediaAssetError as exc:
        db.rollback()
        raise _asset_error(exc) from exc
    return MediaAssetOut.from_domain(asset)
