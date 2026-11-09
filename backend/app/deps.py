"""Dependency injection seam (docs/01 D2).

In Phase 1 this only exposes settings. From Phase 2 onward, provider
instances (NASA POWER, soil, ...) are injected here so tests can substitute
fixture providers and the engine never touches the network.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import Depends

from app.config import Settings, get_settings
from app.errors import FieldShiftError
from data.agronomy_registry import AgronomyRegistry, load_agronomy_registry
from data.providers.base import Provider
from data.providers.nasa_power import NasaPowerProvider

LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def settings_dep() -> Settings:
    """Cached settings for use as a FastAPI dependency."""
    return get_settings()


def agronomy_registry_dep() -> AgronomyRegistry:
    """Load curated agronomy evidence and surface invalid data as a controlled API error."""
    try:
        return load_agronomy_registry()
    except ValueError as exc:
        LOGGER.exception("Curated agronomy registry is invalid")
        raise FieldShiftError(
            code="KNOWLEDGE_DATA_INVALID",
            message="Curated agronomy evidence could not be loaded.",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc


_SETTINGS_DEP = Depends(settings_dep)  # noqa: B008


def nasa_power_provider_dep(settings: Settings = _SETTINGS_DEP) -> Provider | None:
    """Construct the provider only when its explicit experimental gate is enabled."""
    if not settings.nasa_power_enabled:
        return None
    return NasaPowerProvider()
