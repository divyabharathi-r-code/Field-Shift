"""Read-only API endpoints for curated agronomy evidence."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings
from app.deps import agronomy_registry_dep, settings_dep
from data.agronomy_registry import AgronomyRegistry
from schemas.knowledge import (
    AgronomyKnowledgeData,
    AgronomyKnowledgeResponse,
    AgronomySourceResponse,
    CropCalendarClaimResponse,
    CropTraitClaimResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
_REGISTRY_DEP = Depends(agronomy_registry_dep)  # noqa: B008
_SETTINGS_DEP = Depends(settings_dep)  # noqa: B008


@router.get(
    "/agronomy",
    response_model=AgronomyKnowledgeResponse,
    summary="Get curated Madurai agronomy evidence",
    description=(
        "Returns cited Madurai source records, crop claims, and season claims. "
        "Evidence retains its publication, geographic, and production-system scope; "
        "district-level claims are not farm observations or recommendations. "
        "Unknown calendar dates are returned as null with window_status UNKNOWN."
    ),
)
def get_agronomy_evidence(
    registry: AgronomyRegistry = _REGISTRY_DEP,
    settings: Settings = _SETTINGS_DEP,
) -> AgronomyKnowledgeResponse:
    """Return all curated agronomy evidence without scoring or recommendations."""
    return AgronomyKnowledgeResponse(
        api_version=settings.api_version,
        data=AgronomyKnowledgeData(
            scope_notice=(
                "Published Madurai source evidence only; district-level claims are not "
                "farm-level observations or recommendations."
            ),
            sources=[
                AgronomySourceResponse.model_validate(source) for source in registry.sources
            ],
            crop_traits=[
                CropTraitClaimResponse.model_validate(claim)
                for claim in registry.crop_traits
            ],
            crop_calendars=[
                CropCalendarClaimResponse.model_validate(claim)
                for claim in registry.crop_calendars
            ],
        ),
    )
