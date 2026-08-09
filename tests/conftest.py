from __future__ import annotations

import os

import pytest

# Point the app at a throwaway database and data dir BEFORE any app import runs.
_TMP = None


@pytest.fixture
async def client(tmp_path, monkeypatch):
    """An HTTP client against a fresh app instance with an isolated database."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    # Mock provider: instant and reliable by default; failure tests override.
    monkeypatch.setenv("MOCK_MIN_LATENCY", "0")
    monkeypatch.setenv("MOCK_MAX_LATENCY", "0")
    monkeypatch.setenv("MOCK_FAILURE_RATE", "0")

    from app.core.config import get_settings
    from app.core import db as db_module
    from app.providers.financial import reset_provider_state

    get_settings.cache_clear()
    db_module.reset_db_state()
    reset_provider_state()

    from app.models import Base

    engine = db_module.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http:
        yield http

    await engine.dispose()
    get_settings.cache_clear()
    db_module.reset_db_state()
    reset_provider_state()


@pytest.fixture
async def db_session(client):
    """Direct ORM session into the same database the client's app uses (for seeding)."""
    from app.core.db import get_session_factory

    async with get_session_factory()() as session:
        yield session
