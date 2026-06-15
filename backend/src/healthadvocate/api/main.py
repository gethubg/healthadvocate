"""FastAPI application entry point.

Run (from backend/):
    uvicorn healthadvocate.api.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from healthadvocate import __version__
from healthadvocate.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Validate settings and ensure local storage dirs exist on startup."""
    settings = get_settings()
    settings.ensure_dirs()
    yield


def create_app() -> FastAPI:
    """Application factory — keeps construction testable."""
    settings = get_settings()

    app = FastAPI(
        title="HealthAdvocate API",
        version=__version__,
        summary="RAG application for personal bloodwork analysis.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    from healthadvocate.api import routes_query, routes_trends, routes_upload

    app.include_router(routes_upload.router)
    app.include_router(routes_query.router)
    app.include_router(routes_trends.router)

    return app


app = create_app()
