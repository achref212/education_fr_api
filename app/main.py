from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import admin, auth, health, progress
from app.api.routers.content import router as content_router
from app.api.routers.prof import router as prof_router
from app.api.routers.school import router as school_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="DELFy API", version="0.2.0")

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
app.include_router(content_router)
app.include_router(school_router)
app.include_router(prof_router)
