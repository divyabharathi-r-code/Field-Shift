"""GET /health — readiness probe (docs/03 §1).

Exact contract required by Phase 1: the `data` block is
    {"status": "ok", "service": "fieldshift"}
The endpoint-safe extras demanded by docs/03 (engine_version, offline_mode,
cache_warm, sources_available) live alongside it inside the standard success
envelope. `sources_available` stays empty until Phase 2 wires providers —
we never advertise a source that is not actually connected.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from schemas.common import SuccessEnvelope

router = APIRouter(tags=["health"])

# FastAPI idiom: Depends() in a default is intentional; exempt from ruff B008.
_SETTINGS_DEP = Depends(get_settings)  # noqa: B008


@router.get("/health", response_model=SuccessEnvelope, response_model_exclude_none=True)
def health(settings: Settings = _SETTINGS_DEP) -> SuccessEnvelope:
    return SuccessEnvelope(
        api_version=settings.api_version,
        engine_version=settings.engine_version,
        data={
            # --- exact Phase-1 requirement ---
            "status": "ok",
            "service": settings.app_name,  # default: "fieldshift"
            # --- docs/03 readiness extras ---
            "offline_mode": settings.offline_mode,
            "cache_warm": False,          # no cache layer yet (Phase 2)
            "sources_available": [],      # no verified NASA/NOAA sources yet
        },
    )
