"""Tests for zombie run cleanup on server startup."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.db import repository as repo
from app.db.session import init_db


class TestZombieCleanup:
    def test_running_runs_marked_failed_on_cleanup(self, tmp_db: sessionmaker[Session]):
        with tmp_db() as session:
            repo.create_run(session, "r1", "pipe", "story1")
            repo.update_run_status(session, "r1", "running")
            repo.create_run(session, "r2", "pipe", "story2")
            repo.update_run_status(session, "r2", "running")

        with tmp_db() as session:
            cleaned = repo.cleanup_zombie_runs(session)
            assert cleaned == 2

        with tmp_db() as session:
            r1 = repo.get_run(session, "r1")
            r2 = repo.get_run(session, "r2")
            assert r1.status == "failed"
            assert r2.status == "failed"
            assert r1.error == "Server restarted — run interrupted"
            assert r1.finished_at is not None

    def test_pending_runs_also_cleaned(self, tmp_db: sessionmaker[Session]):
        with tmp_db() as session:
            repo.create_run(session, "r1", "pipe", "story1")
            # status starts as "pending" by default

        with tmp_db() as session:
            cleaned = repo.cleanup_zombie_runs(session)
            assert cleaned == 1

        with tmp_db() as session:
            r1 = repo.get_run(session, "r1")
            assert r1.status == "failed"

    def test_completed_runs_not_affected(self, tmp_db: sessionmaker[Session]):
        with tmp_db() as session:
            repo.create_run(session, "r1", "pipe", "story1")
            repo.update_run_status(session, "r1", "completed")
            repo.create_run(session, "r2", "pipe", "story2")
            repo.update_run_status(session, "r2", "failed")

        with tmp_db() as session:
            cleaned = repo.cleanup_zombie_runs(session)
            assert cleaned == 0

        with tmp_db() as session:
            assert repo.get_run(session, "r1").status == "completed"
            assert repo.get_run(session, "r2").status == "failed"

    def test_no_runs_returns_zero(self, tmp_db: sessionmaker[Session]):
        with tmp_db() as session:
            cleaned = repo.cleanup_zombie_runs(session)
            assert cleaned == 0

    def test_cleanup_runs_during_app_startup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        """Integration: zombie runs are cleaned when the app starts."""
        data_dir = tmp_path / "data"
        db_path = data_dir / "opensdlc.db"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Pre-seed DB with a zombie run
        sf = init_db(db_path)
        with sf() as session:
            repo.create_run(session, "zombie1", "pipe", "story")
            repo.update_run_status(session, "zombie1", "running")

        # Patch via env vars — getter functions in config.py read os.environ at call time
        monkeypatch.setenv("OPENSDLC_API_KEY", "")
        monkeypatch.setenv("OPENSDLC_DATA_DIR", str(data_dir))

        from app.main import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        with TestClient(app):
            # After startup, zombie should be cleaned
            with sf() as session:
                r = repo.get_run(session, "zombie1")
                assert r.status == "failed"
                assert "Server restarted" in r.error
