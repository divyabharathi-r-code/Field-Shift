"""Dependency injection seam (docs/01 D2).

In Phase 1 this only exposes settings. From Phase 2 onward, provider
instances (NASA POWER, soil, ...) are injected here so tests can substitute
fixture providers and the engine never touches the network.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings


@lru_cache(maxsize=1)
def settings_dep() -> Settings:
    """Cached settings for use as a FastAPI dependency."""
    return get_settings()
