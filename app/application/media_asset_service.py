from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import Settings
from app.domain.entities import MediaAsset
from app.domain.ports import IMediaAssetRepository

SUPPORTED_ASSET_TYPES = {
    "profile_image",
    "school_logo",
    "audio",
    "image",
    "document",
}
SUPPORTED_OWNER_TYPES = {
    "user",
    "school",
    "story",
    "delf_mock_exam",
    "delf_mock_section",
    "delf_mock_item",
}

IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
AUDIO_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/webm",
}
DOCUMENT_MIME_TYPES = {"application/pdf"}

_SAFE_SUFFIX = re.compile(r"[^a-zA-Z0-9]+")


class MediaAssetError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class MediaAssetService:
    def __init__(self, repo: IMediaAssetRepository, settings: Settings) -> None:
        self._repo = repo
        self._settings = settings

    def register_url(
        self,
        *,
        owner_type: str | None,
        owner_id: UUID | None,
        asset_type: str,
        title: str | None,
        url: str,
        metadata: dict | None = None,
    ) -> MediaAsset:
        self._validate_owner(owner_type, owner_id)
        self._validate_asset_type(asset_type)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise MediaAssetError("invalid_url", "L'URL doit commencer par http ou https")
        return self._repo.create(
            owner_type=owner_type,
            owner_id=owner_id,
            asset_type=asset_type,
            title=title,
            url=url,
            storage_path=None,
            mime_type=None,
            size_bytes=None,
            metadata=metadata or {},
        )

    def list_assets(
        self,
        *,
        owner_type: str | None = None,
        owner_id: UUID | None = None,
        asset_type: str | None = None,
        is_active: bool | None = True,
    ) -> list[MediaAsset]:
        if owner_type is not None and owner_type not in SUPPORTED_OWNER_TYPES:
            raise MediaAssetError("invalid_owner_type", "Type de propriétaire invalide")
        if asset_type is not None and asset_type not in SUPPORTED_ASSET_TYPES:
            raise MediaAssetError("invalid_asset_type", "Type de ressource invalide")
        return self._repo.list_all(
            owner_type=owner_type,
            owner_id=owner_id,
            asset_type=asset_type,
            is_active=is_active,
        )

    def archive(self, asset_id: UUID) -> MediaAsset:
        asset = self._repo.archive(asset_id)
        if asset is None:
            raise MediaAssetError("not_found", "Ressource introuvable")
        return asset

    def save_upload(
        self,
        *,
        file: UploadFile,
        owner_type: str | None,
        owner_id: UUID | None,
        asset_type: str,
        title: str | None,
        metadata: dict | None = None,
    ) -> MediaAsset:
        self._validate_owner(owner_type, owner_id)
        self._validate_asset_type(asset_type)
        mime_type = self._detect_mime_type(file)
        self._validate_mime_type(asset_type, mime_type)

        folder = self._folder_for(asset_type)
        media_root = Path(self._settings.media_root)
        target_dir = media_root / folder
        target_dir.mkdir(parents=True, exist_ok=True)

        suffix = self._safe_suffix(file.filename, mime_type)
        storage_name = f"{uuid4().hex}{suffix}"
        storage_path = str(Path(folder) / storage_name)
        target_path = target_dir / storage_name

        max_bytes = self._max_bytes(asset_type)
        written = 0
        try:
            with target_path.open("wb") as out:
                while True:
                    chunk = file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        out.close()
                        target_path.unlink(missing_ok=True)
                        raise MediaAssetError("file_too_large", "Fichier trop volumineux")
                    out.write(chunk)
        finally:
            file.file.seek(0)

        if written == 0:
            target_path.unlink(missing_ok=True)
            raise MediaAssetError("empty_file", "Fichier vide")

        url_prefix = self._settings.media_url_prefix.rstrip("/")
        url = f"{url_prefix}/{storage_path}"
        return self._repo.create(
            owner_type=owner_type,
            owner_id=owner_id,
            asset_type=asset_type,
            title=title or file.filename,
            url=url,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=written,
            metadata=metadata or {},
        )

    def _validate_owner(self, owner_type: str | None, owner_id: UUID | None) -> None:
        if owner_type is None and owner_id is not None:
            raise MediaAssetError("invalid_owner", "ownerType est requis avec ownerId")
        if owner_type is not None and owner_type not in SUPPORTED_OWNER_TYPES:
            raise MediaAssetError("invalid_owner_type", "Type de propriétaire invalide")

    def _validate_asset_type(self, asset_type: str) -> None:
        if asset_type not in SUPPORTED_ASSET_TYPES:
            raise MediaAssetError("invalid_asset_type", "Type de ressource invalide")

    def _detect_mime_type(self, file: UploadFile) -> str:
        mime_type = (file.content_type or "").split(";")[0].strip().lower()
        if not mime_type and file.filename:
            mime_type = mimetypes.guess_type(file.filename)[0] or ""
        if not mime_type:
            raise MediaAssetError("invalid_mime_type", "Type de fichier inconnu")
        return mime_type

    def _validate_mime_type(self, asset_type: str, mime_type: str) -> None:
        if asset_type in ("profile_image", "school_logo", "image"):
            allowed = IMAGE_MIME_TYPES
        elif asset_type == "audio":
            allowed = AUDIO_MIME_TYPES
        else:
            allowed = DOCUMENT_MIME_TYPES
        if mime_type not in allowed:
            raise MediaAssetError("invalid_mime_type", "Type de fichier non supporté")

    def _safe_suffix(self, filename: str | None, mime_type: str) -> str:
        suffix = Path(filename or "").suffix.lower()
        if not suffix:
            suffix = mimetypes.guess_extension(mime_type) or ".bin"
        suffix = _SAFE_SUFFIX.sub("", suffix)
        return f".{suffix.lstrip('.')}" if suffix else ".bin"

    def _folder_for(self, asset_type: str) -> str:
        if asset_type in ("profile_image", "school_logo", "image"):
            return "images"
        if asset_type == "audio":
            return "audio"
        return "documents"

    def _max_bytes(self, asset_type: str) -> int:
        if asset_type in ("profile_image", "school_logo", "image"):
            return self._settings.max_image_mb * 1024 * 1024
        if asset_type == "audio":
            return self._settings.max_audio_mb * 1024 * 1024
        return self._settings.max_document_mb * 1024 * 1024
