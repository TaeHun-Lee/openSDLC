"""FastAPI application factory for OpenSDLC backend."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import agents, health, pipelines, runs
from app.services.print_capture import install_print_hook
from app.services.run_manager import RunManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize and cleanup shared resources."""
    # Install global print interceptor
    install_print_hook()

    # Initialize run manager
    app.state.run_manager = RunManager(max_concurrent=2)

    yield

    # Cleanup (nothing critical to do)


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenSDLC API",
        description="AI Software Factory pipeline orchestration API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow all origins for dev; restrict in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(health.router, prefix="/api")
    app.include_router(pipelines.router, prefix="/api")
    app.include_router(agents.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")

    return app


app = create_app()
