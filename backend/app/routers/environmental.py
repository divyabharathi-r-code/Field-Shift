"""Experimental read-only environmental data API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.config import Settings
from app.deps import nasa_power_provider_dep, settings_dep
from app.errors import (
    CACHE_ERROR,
    PROVIDER_UNAVAILABLE,
    SOURCE_DISABLED,
    UPSTREAM_INVALID_RESPONSE,
    VALIDATION_ERROR,
    FieldShiftError,
)
from data.cache import CacheError
from data.providers.base import DataQuery, Provider
from data.providers.nasa_power import PowerResponseError, PowerUnavailableError
from data.registry import NASA_POWER
from schemas.environmental import (
    EnvironmentalDailyData,
    EnvironmentalDailyRequest,
    EnvironmentalDailyResponse,
    EnvironmentalObservationResponse,
    NasaPowerProvenanceResponse,
    ParameterMetadataResponse,
)

router = APIRouter(prefix="/environmental", tags=["environmental"])
_PROVIDER_DEP = Depends(nasa_power_provider_dep)  # noqa: B008
_SETTINGS_DEP = Depends(settings_dep)  # noqa: B008


@router.get(
    "/daily",
    response_model=EnvironmentalDailyResponse,
    summary="Get experimental NASA POWER daily data",
    description=(
        "Returns NASA POWER daily precipitation and temperature series for caller-supplied "
        "coordinates and an inclusive date range. Access is disabled by default because the "
        "source remains unverified. When enabled, results are experimental provider-gridded "
        "context, not farm-station observations. Dates use UTC; missing values are null."
    ),
    responses={
        400: {"description": "Invalid coordinates or date range"},
        500: {"description": "Cache read failure"},
        502: {"description": "Invalid NASA POWER response"},
        503: {"description": "Source disabled or provider unavailable"},
    },
)
def get_daily_environment(
    request: Annotated[EnvironmentalDailyRequest, Query()],
    provider: Provider | None = _PROVIDER_DEP,
    settings: Settings = _SETTINGS_DEP,
) -> EnvironmentalDailyResponse:
    """Fetch normalized NASA POWER observations without deriving indicators."""
    if request.start_date > request.end_date:
        raise FieldShiftError(
            code=VALIDATION_ERROR,
            message="Request body/query failed schema validation.",
            status_code=400,
            details={
                "errors": [
                    {
                        "loc": ["query", "start_date"],
                        "msg": "start_date must not be after end_date",
                    }
                ]
            },
        )
    if provider is None:
        raise FieldShiftError(
            code=SOURCE_DISABLED,
            message="NASA POWER access is disabled because the source is unverified.",
            status_code=503,
        )
    query = DataQuery(
        latitude=request.latitude,
        longitude=request.longitude,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    try:
        result = provider.fetch(query, offline=settings.offline_mode)
    except PowerUnavailableError as exc:
        raise FieldShiftError(
            code=PROVIDER_UNAVAILABLE,
            message="NASA POWER data are unavailable for this request.",
            status_code=503,
            details={"reason": str(exc)},
        ) from exc
    except PowerResponseError as exc:
        raise FieldShiftError(
            code=UPSTREAM_INVALID_RESPONSE,
            message="NASA POWER returned an invalid response.",
            status_code=502,
            details={"reason": str(exc)},
        ) from exc
    except CacheError as exc:
        raise FieldShiftError(
            code=CACHE_ERROR,
            message="The NASA POWER response cache could not be read.",
            status_code=500,
            details={"reason": str(exc)},
        ) from exc

    provenance = result.provenance
    return EnvironmentalDailyResponse(
        api_version=settings.api_version,
        data=EnvironmentalDailyData(
            experimental=True,
            source_verification_status=NASA_POWER.verification_status,
            observations=[
                EnvironmentalObservationResponse.model_validate(observation)
                for observation in result.observations
            ],
        ),
        provenance=[
            NasaPowerProvenanceResponse(
                source_id=provenance.source_id,
                source_type=provenance.source_type,
                provider=provenance.provider,
                product=provenance.product,
                endpoint=provenance.endpoint,
                retrieved_at=provenance.retrieved_at,
                latitude=provenance.latitude,
                longitude=provenance.longitude,
                reported_latitude=provenance.reported_latitude,
                reported_longitude=provenance.reported_longitude,
                requested_start_date=provenance.requested_start_date,
                requested_end_date=provenance.requested_end_date,
                returned_start_date=provenance.returned_start_date,
                returned_end_date=provenance.returned_end_date,
                time_standard=provenance.time_standard,
                source_names=list(provenance.source_names),
                parameters=list(provenance.parameters),
                parameter_metadata=[
                    ParameterMetadataResponse(
                        parameter=parameter,
                        units=metadata.units,
                        description=metadata.description,
                    )
                    for parameter, metadata in provenance.parameter_metadata
                ],
                limitations=list(provenance.limitations),
            )
        ],
    )
