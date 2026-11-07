"""Wire-contract primitives shared by all response models (docs/03 §0.3).

Phase 1 ships only what `/health` needs plus the provenance/confidence types
that every future endpoint must reuse — defined once so routers cannot drift.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DataClass(StrEnum):
    """Every number in the system is tagged with one of these (docs/00)."""

    OBSERVED = "OBSERVED"        # measured by a provider (NASA/NOAA/USDA)
    DERIVED = "DERIVED"          # computed from observed data (documented formula)
    ASSUMPTION = "ASSUMPTION"    # curated knowledge table / expert rule
    SIMULATED = "SIMULATED"      # scenario perturbation output


class Provenance(BaseModel):
    source_id: str
    class_: DataClass = Field(alias="class")
    retrieved_at: str | None = None
    resolution: str | None = None
    temporal_step: str | None = None
    units: str | None = None
    method: str | None = None
    citation: str | None = None
    formula: str | None = None
    assumption_rationale: str | None = None
    sensitivity_range: list[float] | None = None

    model_config = {"populate_by_name": True}


class FieldWarning(BaseModel):
    code: str
    severity: str = "warning"  # info | warning | critical
    field_path: str | None = None
    message: str


class Confidence(BaseModel):
    level: str = "unknown"  # low | medium | high | unknown
    coverage_pct: float | None = None
    reasons: list[str] = Field(default_factory=list)


class SuccessEnvelope(BaseModel):
    """Minimum shape of every 2xx body (docs/03 §0.1)."""

    api_version: str
    data: dict[str, Any]
    provenance: list[Provenance] = Field(default_factory=list)
    warnings: list[FieldWarning] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    run_id: str | None = None
    engine_version: str | None = None
    determinism_key: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    warnings: list[FieldWarning] = Field(default_factory=list)


class ErrorEnvelope(BaseModel):
    error: ErrorBody
