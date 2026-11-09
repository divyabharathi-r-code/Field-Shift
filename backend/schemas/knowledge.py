"""Wire models for read-only curated agronomy evidence."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schemas.common import Confidence, FieldWarning, Provenance, SuccessEnvelope

ProductionSystem = Literal["IRRIGATED", "RAINFED", "UNKNOWN"]
EvidenceStatus = Literal["VERIFIED", "UNVERIFIED"]
TimeApplicability = Literal["HISTORICAL", "CURRENT", "UNKNOWN"]
EvidenceKind = Literal["PUBLISHED_STATISTIC", "PUBLISHED_DESCRIPTIVE_CLAIM"]
WindowStatus = Literal["KNOWN", "UNKNOWN"]


class AgronomySourceResponse(BaseModel):
    """Source metadata for a cited agronomy claim."""

    model_config = ConfigDict(from_attributes=True)

    source_id: str
    provider: str
    title: str
    publication_year: int | None
    version: str | None
    url: str
    accessed_date: date
    geographic_scope: str
    source_kind: str
    verification_status: EvidenceStatus
    time_applicability: TimeApplicability
    notes: str


class CropTraitClaimResponse(BaseModel):
    """A source-cited crop claim; not a farm-level observation or recommendation."""

    model_config = ConfigDict(from_attributes=True)

    record_id: str
    crop_id: str
    crop_name: str
    claim: str
    value: str
    unit: str | None
    source_id: str
    source_locator: str
    geographic_scope: str
    production_system_scope: ProductionSystem
    evidence_kind: EvidenceKind
    evidence_status: EvidenceStatus
    time_applicability: TimeApplicability
    reference_period: str | None
    notes: str


class CropCalendarClaimResponse(BaseModel):
    """A cited season record; unknown date windows are represented as null."""

    model_config = ConfigDict(from_attributes=True)

    record_id: str
    crop_id: str
    crop_name: str
    season: str
    activity: str
    window_start: date | None
    window_end: date | None
    window_status: WindowStatus
    timing_note: str | None
    source_id: str
    source_locator: str
    geographic_scope: str
    production_system_scope: ProductionSystem
    evidence_kind: EvidenceKind
    evidence_status: EvidenceStatus
    time_applicability: TimeApplicability
    reference_period: str | None
    notes: str


class AgronomyKnowledgeData(BaseModel):
    """Curated source-cited claims kept separate from farm-supplied observations."""

    scope_notice: str = Field(
        description=(
            "Published Madurai source evidence only; district-level claims are not "
            "farm-level observations or recommendations."
        )
    )
    sources: list[AgronomySourceResponse]
    crop_traits: list[CropTraitClaimResponse]
    crop_calendars: list[CropCalendarClaimResponse]


class AgronomyKnowledgeResponse(SuccessEnvelope):
    """Standard API success envelope with a typed agronomy evidence payload."""

    data: AgronomyKnowledgeData
    provenance: list[Provenance] = Field(default_factory=list)
    warnings: list[FieldWarning] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
