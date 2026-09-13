"""Точка входу FastAPI-застосунку RunTracker."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import plans, runners, runs, shoes

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Створює схему БД перед прийомом запитів."""
    init_db()
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runners.router)
app.include_router(runs.router)
app.include_router(shoes.router)
app.include_router(plans.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": settings.version}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")
