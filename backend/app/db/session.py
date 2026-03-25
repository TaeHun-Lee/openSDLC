"""Database engine and session factory initialization."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base

logger = logging.getLogger(__name__)


def _run_alembic_upgrade(db_url: str) -> bool:
    """Run alembic upgrade head programmatically.

    Returns True on success, False if alembic is unavailable or migration fails.
    """
    try:
        from alembic import command
        from alembic.config import Config

        # Locate alembic.ini relative to the backend directory
        backend_dir = Path(__file__).resolve().parent.parent.parent
        ini_path = backend_dir / "alembic.ini"

        if not ini_path.is_file():
            logger.debug("alembic.ini not found at %s — skipping migration", ini_path)
            return False

        alembic_cfg = Config(str(ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")
        return True
    except Exception as exc:
        logger.warning("Alembic migration failed (%s) — falling back to create_all", exc)
        return False


def init_db(db_path: Path, *, run_migrations: bool = True) -> sessionmaker[Session]:
    """Create engine, ensure tables exist, return a session factory.

    Args:
        db_path: Path to the SQLite database file.
        run_migrations: If True (default), attempt Alembic migrations first.
            Falls back to create_all() if Alembic is unavailable or fails.
            Set to False for test fixtures that use temporary databases.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    if run_migrations:
        migrated = _run_alembic_upgrade(db_url)
        if not migrated:
            Base.metadata.create_all(engine)
    else:
        # Direct table creation for tests (no migration history needed)
        Base.metadata.create_all(engine)

    return sessionmaker(bind=engine, expire_on_commit=False)
