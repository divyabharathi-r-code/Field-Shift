"""App settings from environment (pydantic-settings).

Phase 1 scope: only fields that exist today. NASA/provider keys and cache
settings are added in Phase 2 when the data layer lands. Secrets are never
committed; copy .env.example -> .env locally.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FS_", extra="ignore")

    app_name: str = "fieldshift"
    api_version: str = "v1"
    engine_version: str = "0.1.0"
    debug: bool = False
    # Offline mode is a *statement of intent* for the demo: with no providers
    # wired yet (Phase 1), the backend is offline by definition.
    offline_mode: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]


def get_settings() -> Settings:
    """Single factory used by FastAPI dependency injection (app/deps.py)."""
    return Settings()
