"""Source metadata used by provider results and data provenance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from data.providers.base import SourceType

VerificationStatus = Literal["unverified", "verified", "failed"]


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    provider: str
    product_or_dataset: str
    source_type: SourceType
    purpose_in_app: str
    access_url: str
    access_method: str
    authentication_required: bool | None
    temporal_resolution: str
    parameters: tuple[str, ...]
    units_by_parameter: tuple[tuple[str, str], ...]
    spatial_resolution: str | None
    historical_coverage: str | None
    validated_domain: str | None
    licence: str | None
    citation: str
    cache_ttl_days: int
    verification_status: VerificationStatus
    verification_notes: str


NASA_POWER = SourceRecord(
    source_id="NASA_POWER",
    title="NASA Prediction Of Worldwide Energy Resources (POWER) Daily Point API",
    provider="NASA POWER",
    product_or_dataset="POWER Daily Point meteorology",
    source_type="PROVIDER_GRIDDED",
    purpose_in_app=(
        "Provide daily precipitation and temperature context for the environmental profile."
    ),
    access_url="https://power.larc.nasa.gov/api/temporal/daily/point",
    access_method="HTTPS JSON API",
    authentication_required=None,
    temporal_resolution="Daily",
    parameters=("PRECTOTCORR", "T2M_MAX", "T2M_MIN"),
    units_by_parameter=(
        ("PRECTOTCORR", "mm/day"),
        ("T2M_MAX", "C"),
        ("T2M_MIN", "C"),
    ),
    spatial_resolution=None,
    historical_coverage=None,
    validated_domain=None,
    licence=None,
    citation="https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
    cache_ttl_days=7,
    verification_status="unverified",
    verification_notes=(
        "A sample request returned JSON with the expected parameters, units, fill value, "
        "and UTC metadata. Parameter-specific spatial resolution, historical coverage, "
        "licence terms, and request limits remain to be verified before a source is "
        "reachable from a shipped demo path."
    ),
)

SOURCE_REGISTRY: dict[str, SourceRecord] = {NASA_POWER.source_id: NASA_POWER}
