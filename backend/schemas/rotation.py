"""Wire contracts for user-supplied rotation plans and structural validation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

NonBlankString = Annotated[StrictStr, Field(min_length=1)]


class RotationCropEntryInput(BaseModel):
    """One user-identified crop at an explicit, one-based sequence position."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence_position: Annotated[StrictInt, Field(ge=1)]
    crop_id: NonBlankString | None = None
    crop_name: NonBlankString | None = None

    @field_validator("crop_id", "crop_name")
    @classmethod
    def reject_blank_crop_identity(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("crop identity must not be blank")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_one_crop_identity(self) -> RotationCropEntryInput:
        if (self.crop_id is None) == (self.crop_name is None):
            raise ValueError("provide exactly one of crop_id or crop_name")
        return self


class RotationPlanInput(BaseModel):
    """Ordered rotation sequence supplied by the caller; no crops are inferred."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: Annotated[tuple[RotationCropEntryInput, ...], Field(min_length=1)]


class RotationPlanValidationIssue(BaseModel):
    """Machine-readable structural validation issue; entry_index is zero-based."""

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


class RotationPlanValidationResult(BaseModel):
    """Structural status only; agronomic suitability is explicitly not assessed."""

    structurally_valid: bool
    issues: tuple[RotationPlanValidationIssue, ...]
    suitability_assessment: Literal["NOT_ASSESSED"] = "NOT_ASSESSED"
