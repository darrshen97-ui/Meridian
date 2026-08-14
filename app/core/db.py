"""Async database engine and session factory."""
from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _ensure_sqlite_dir(url: str) -> None:
    """Create the directory a SQLite file lives in, if it doesn't exist.

    Uses SQLAlchemy's own URL parser: naive string splitting drops the leading
    slash of an absolute path (sqlite:////tmp/x.db), which silently rewrites it
    to a relative one. Local runs use a relative path and never hit that; the
    container deployment uses an absolute one and did (docs/DECISIONS.md D-027).
    """
    if not url.startswith("sqlite"):
        return
    database = make_url(url).database
    if database and database != ":memory:":
        Path(database).parent.mkdir(parents=True, exist_ok=True)


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _ensure_sqlite_dir(settings.database_url)
        _engine = create_async_engine(settings.async_database_url)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request."""
    async with get_session_factory()() as session:
        yield session


def reset_db_state() -> None:
    """Testing hook: forget the cached engine/factory so a new DATABASE_URL takes effect."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
