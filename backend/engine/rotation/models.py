"""Pure domain models for explicitly user-supplied rotation plans."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class RotationCropEntry:
    sequence_position: int
    crop_id: str | None = None
    crop_name: str | None = None


@dataclass(frozen=True, slots=True)
class RotationPlan:
    entries: tuple[RotationCropEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entries, (list, tuple)):
            raise TypeError("RotationPlan.entries must be a list or tuple")
        object.__setattr__(self, "entries", tuple(self.entries))


@dataclass(frozen=True, slots=True)
class PlanValidationIssue:
    code: Literal[
        "INVALID_ENTRY",
        "INVALID_SEQUENCE_POSITION",
        "DUPLICATE_SEQUENCE_POSITION",
        "SEQUENCE_ORDER_MISMATCH",
        "MISSING_CROP_IDENTITY",
        "AMBIGUOUS_CROP_IDENTITY",
        "BLANK_CROP_IDENTITY",
    ]
    entry_index: int | None
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class PlanValidationResult:
    structurally_valid: bool
    issues: tuple[PlanValidationIssue, ...]
    suitability_assessment: Literal["NOT_ASSESSED"] = "NOT_ASSESSED"
