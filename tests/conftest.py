import os

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure a dummy DATABASE_URL for imports when running tests that don't hit DB
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://test:test@localhost:5432/test",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only")

from app.main import app  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
