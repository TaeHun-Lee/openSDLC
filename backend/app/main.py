"""FastAPI application factory for OpenSDLC backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS, DATA_DIR, DATABASE_PATH, RUNS_DIR
from app.db.session import init_db
from app.routers import agents, health, pipelines, projects, runs
from app.services.print_capture import install_print_hook
from app.services.run_manager import RunManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize and cleanup shared resources."""
    # Install global print interceptor
    install_print_hook()

    # Ensure data directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize database
    session_factory = init_db(DATABASE_PATH)
    app.state.session_factory = session_factory

    # Initialize run manager with DB access
    app.state.run_manager = RunManager(
        session_factory=session_factory,
        max_concurrent=2,
    )

    yield

    # Cleanup (nothing critical to do)


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenSDLC API",
        description="AI Software Factory pipeline orchestration API",
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS — configurable via OPENSDLC_CORS_ORIGINS env var (comma-separated)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(health.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    app.include_router(pipelines.router, prefix="/api")
    app.include_router(agents.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")

    return app


app = create_app()
