from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_db, get_media_asset_service, require_admin
from app.application.media_asset_service import MediaAssetService
from app.core.config import get_settings
from app.domain.entities import MediaAsset, User
from app.main import app


def _admin_user() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        level="admin",
        created_at=datetime.now(timezone.utc),
        role="admin",
    )


class FakeDb:
    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


class InMemoryMediaAssetRepo:
    def __init__(self) -> None:
        self.assets: list[MediaAsset] = []

    def create(
        self,
        *,
        owner_type,
        owner_id,
        asset_type,
        title,
        url,
        storage_path,
        mime_type,
        size_bytes,
        metadata=None,
    ) -> MediaAsset:
        now = datetime.now(timezone.utc)
        asset = MediaAsset(
            id=uuid4(),
            owner_type=owner_type,
            owner_id=owner_id,
            asset_type=asset_type,
            title=title,
            url=url,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            metadata=metadata or {},
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.assets.append(asset)
        return asset

    def list_all(
        self,
        *,
        owner_type=None,
        owner_id=None,
        asset_type=None,
        is_active=True,
    ) -> list[MediaAsset]:
        items = self.assets
        if owner_type is not None:
            items = [asset for asset in items if asset.owner_type == owner_type]
        if owner_id is not None:
            items = [asset for asset in items if asset.owner_id == owner_id]
        if asset_type is not None:
            items = [asset for asset in items if asset.asset_type == asset_type]
        if is_active is not None:
            items = [asset for asset in items if asset.is_active == is_active]
        return items

    def archive(self, asset_id):
        for index, asset in enumerate(self.assets):
            if asset.id == asset_id:
                archived = MediaAsset(
                    **{**asset.__dict__, "is_active": False, "updated_at": datetime.now(timezone.utc)}
                )
                self.assets[index] = archived
                return archived
        return None


@pytest.fixture
async def media_client(tmp_path, monkeypatch):
    repo = InMemoryMediaAssetRepo()
    settings = get_settings()
    settings.media_root = str(tmp_path / "media")
    settings.media_url_prefix = "/media"
    for route in app.routes:
        if getattr(route, "name", None) == "media":
            route.app.directory = settings.media_root
            route.app.all_directories = [settings.media_root]

    def override_db():
        yield FakeDb()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_admin] = _admin_user
    app.dependency_overrides[get_media_asset_service] = lambda: MediaAssetService(
        repo, settings
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, repo
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_admin_uploads_image_and_static_url_is_readable(media_client) -> None:
    client, repo = media_client

    response = await client.post(
        "/admin/assets/upload",
        data={
            "assetType": "profile_image",
            "ownerType": "user",
            "ownerId": str(uuid4()),
            "title": "Photo profil",
        },
        files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["assetType"] == "profile_image"
    assert data["url"].startswith("/media/images/")
    assert data["sizeBytes"] == 8

    static_response = await client.get(data["url"])
    assert static_response.status_code == 200
    assert static_response.content == b"\x89PNG\r\n\x1a\n"

    assert len(repo.assets) == 1


@pytest.mark.anyio
async def test_admin_uploads_webm_audio_and_static_url_is_readable(media_client) -> None:
    client, repo = media_client

    response = await client.post(
        "/admin/assets/upload",
        data={
            "assetType": "audio",
            "title": "Audio enregistré",
        },
        files={"file": ("recording.webm", b"\x1a\x45\xdf\xa3webm", "audio/webm")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["assetType"] == "audio"
    assert data["url"].startswith("/media/audio/")
    assert data["mimeType"] == "audio/webm"
    assert data["sizeBytes"] == 8

    static_response = await client.get(data["url"])
    assert static_response.status_code == 200
    assert static_response.content == b"\x1a\x45\xdf\xa3webm"

    assert len(repo.assets) == 1


@pytest.mark.anyio
async def test_admin_upload_rejects_wrong_mime_type(media_client) -> None:
    client, _engine = media_client

    response = await client.post(
        "/admin/assets/upload",
        data={"assetType": "audio"},
        files={"file": ("audio.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Type de fichier non supporté"


@pytest.mark.anyio
async def test_admin_registers_and_archives_external_url(media_client) -> None:
    client, _engine = media_client

    created = await client.post(
        "/admin/assets",
        json={
            "assetType": "audio",
            "ownerType": "story",
            "ownerId": str(uuid4()),
            "title": "Lecture",
            "url": "https://cdn.example.com/story.mp3",
        },
    )

    assert created.status_code == 201
    asset_id = created.json()["id"]

    listed = await client.get("/admin/assets", params={"assetType": "audio"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [asset_id]

    archived = await client.delete(f"/admin/assets/{asset_id}")
    assert archived.status_code == 200
    assert archived.json()["isActive"] is False

    listed_active = await client.get("/admin/assets", params={"assetType": "audio"})
    assert listed_active.status_code == 200
    assert listed_active.json() == []
