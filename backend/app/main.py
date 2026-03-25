"""FastAPI application factory for OpenSDLC backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_api_key
from app.core.config import get_cors_origins, get_data_dir, get_database_path, get_runs_dir
from app.db import repository as repo
from app.db.session import init_db
from app.routers import agents, health, pipelines, projects, runs
from app.services.run_manager import RunManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize and cleanup shared resources."""
    # Ensure data directories exist
    get_data_dir().mkdir(parents=True, exist_ok=True)
    get_runs_dir().mkdir(parents=True, exist_ok=True)

    # Initialize database
    session_factory = init_db(get_database_path())
    app.state.session_factory = session_factory

    # Clean up zombie runs from previous crash/restart
    with session_factory() as session:
        cleaned = repo.cleanup_zombie_runs(session)
        if cleaned:
            logger.warning("Cleaned up %d zombie run(s) from previous session", cleaned)

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
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers — health is public, others require API key (when configured)
    app.include_router(health.router, prefix="/api")
    auth_deps = [Depends(require_api_key)]
    app.include_router(projects.router, prefix="/api", dependencies=auth_deps)
    app.include_router(pipelines.router, prefix="/api", dependencies=auth_deps)
    app.include_router(agents.router, prefix="/api", dependencies=auth_deps)
    app.include_router(runs.router, prefix="/api", dependencies=auth_deps)

    return app


app = create_app()
