from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from starlette.datastructures import Headers
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_avatar_image_service,
    get_current_account,
    get_current_user,
    get_media_asset_service,
    require_admin,
)
from app.api.schemas.media_asset import (
    MediaAssetCreateIn,
    MediaAssetOut,
    ProfileAvatarGenerateIn,
)
from app.application.avatar_image_service import AvatarImageError, AvatarImageService
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


@account_router.post(
    "/profile-avatar/generate",
    response_model=MediaAssetOut,
    status_code=status.HTTP_201_CREATED,
)
def generate_current_user_profile_avatar(
    body: ProfileAvatarGenerateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    media_service: MediaAssetService = Depends(get_media_asset_service),
    avatar_service: AvatarImageService = Depends(get_avatar_image_service),
) -> MediaAssetOut:
    try:
        generated = avatar_service.generate(
            style=body.style,
            customization=body.customization,
            prompt=body.prompt,
        )
        upload = UploadFile(
            file=BytesIO(generated.image_bytes),
            size=len(generated.image_bytes),
            filename=_avatar_filename(generated.mime_type),
            headers=Headers({"content-type": generated.mime_type}),
        )
        asset = media_service.save_upload(
            file=upload,
            owner_type="user",
            owner_id=user.id,
            asset_type="profile_image",
            title=f"Avatar {user.first_name} {user.last_name}",
            metadata={
                "source": "ai_avatar",
                "provider": generated.provider,
                "model": generated.model,
                "style": body.style,
                "prompt": generated.prompt,
                "customization": body.customization,
            },
        )
        db.commit()
    except AvatarImageError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        ) from exc
    except MediaAssetError as exc:
        db.rollback()
        raise _asset_error(exc) from exc
    return MediaAssetOut.from_domain(asset)


def _avatar_filename(mime_type: str) -> str:
    if mime_type == "image/jpeg":
        return "avatar.jpg"
    if mime_type == "image/webp":
        return "avatar.webp"
    return "avatar.png"
