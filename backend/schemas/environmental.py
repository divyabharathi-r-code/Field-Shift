"""Wire models for the experimental NASA POWER daily environmental endpoint."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.common import Confidence, FieldWarning, SuccessEnvelope

SourceType = Literal["PROVIDER_GRIDDED"]
ObservationStatus = Literal["ok", "missing"]
SourceVerificationStatus = Literal["unverified"]


class EnvironmentalDailyRequest(BaseModel):
    """Caller-supplied location and inclusive date range for NASA POWER."""

    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    start_date: date
    end_date: date

class EnvironmentalObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    parameter: str
    value: float | None
    units: str
    status: ObservationStatus


class ParameterMetadataResponse(BaseModel):
    parameter: str
    units: str
    description: str


class NasaPowerProvenanceResponse(BaseModel):
    """Complete provenance returned by the NASA POWER provider."""

    model_config = ConfigDict(from_attributes=True)

    source_id: str
    source_type: SourceType
    provider: str
    product: str
    endpoint: str
    retrieved_at: datetime
    latitude: float
    longitude: float
    reported_latitude: float
    reported_longitude: float
    requested_start_date: date
    requested_end_date: date
    returned_start_date: date
    returned_end_date: date
    time_standard: str
    source_names: list[str]
    parameters: list[str]
    parameter_metadata: list[ParameterMetadataResponse]
    limitations: list[str]


class EnvironmentalDailyData(BaseModel):
    experimental: Literal[True] = True
    source_verification_status: SourceVerificationStatus = "unverified"
    observations: list[EnvironmentalObservationResponse]


class EnvironmentalDailyResponse(SuccessEnvelope):
    """Standard envelope with typed observations and full provider provenance."""

    data: EnvironmentalDailyData
    provenance: list[NasaPowerProvenanceResponse]
    warnings: list[FieldWarning] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
