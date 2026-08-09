"""Application configuration.

All settings come from the environment (or a local `.env`), with working defaults so the
app runs with no configuration at all. See `.env.example` for documentation of each value.
"""
from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///data/meridian.db"
    port: int = 8787
    data_dir: Path = Path("data")

    jwt_secret: str | None = None
    session_hours: int = 24
    cookie_secure: bool = False  # enabled in deployed (HTTPS) configuration only

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    llm_provider: str = "ollama"
    anthropic_api_key: str | None = None

    def resolve_jwt_secret(self) -> str:
        """Explicit secret if configured, otherwise one generated once and persisted.

        Auto-generation keeps the double-click zip working without any setup while
        still surviving restarts (sessions are not invalidated on every launch).
        """
        if self.jwt_secret:
            return self.jwt_secret
        secret_file = self.data_dir / ".jwt_secret"
        if secret_file.exists():
            return secret_file.read_text().strip()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_urlsafe(48)
        secret_file.write_text(secret)
        try:
            secret_file.chmod(0o600)
        except OSError:  # not supported on some Windows filesystems
            pass
        return secret

    @property
    def async_database_url(self) -> str:
        """Map the plain DATABASE_URL onto its async driver."""
        url = self.database_url
        if url.startswith("sqlite://"):
            return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Plain URL for Alembic and other sync-only tooling."""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
