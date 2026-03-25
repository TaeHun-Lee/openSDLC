"""Shared test fixtures for OpenSDLC backend tests."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import init_db


@pytest.fixture()
def tmp_db(tmp_path: Path) -> sessionmaker[Session]:
    """Create a temporary SQLite database and return a session factory."""
    db_path = tmp_path / "test.db"
    return init_db(db_path, run_migrations=False)


@pytest.fixture()
def test_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient with a temporary database and no auth."""
    monkeypatch.setenv("OPENSDLC_API_KEY", "")
    monkeypatch.setenv("OPENSDLC_DATA_DIR", str(tmp_path / "data"))

    from app.main import create_app

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


@pytest.fixture()
def authed_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient with API key authentication enabled."""
    monkeypatch.setenv("OPENSDLC_API_KEY", "test-secret-key")
    monkeypatch.setenv("OPENSDLC_DATA_DIR", str(tmp_path / "data"))

    from app.main import create_app

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
