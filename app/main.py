from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routers import admin, assets, auth, health, progress
from app.api.routers.content import router as content_router
from app.api.routers.delf_tests import router as delf_tests_router
from app.api.routers.multiplayer import router as multiplayer_router
from app.api.routers.parcours import router as parcours_router
from app.api.routers.prof import router as prof_router
from app.api.routers.school import router as school_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="DELFy API", version="0.2.0")

Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount(
    settings.media_url_prefix.rstrip("/") or "/media",
    StaticFiles(directory=settings.media_root),
    name="media",
)

_origins = (
    [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if settings.cors_origins != "*"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(progress.router)
app.include_router(admin.router)
app.include_router(assets.router)
app.include_router(assets.account_router)
app.include_router(content_router)
app.include_router(delf_tests_router)
app.include_router(parcours_router)
app.include_router(multiplayer_router)
app.include_router(school_router)
app.include_router(prof_router)
