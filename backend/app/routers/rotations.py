"""HTTP endpoint for structural validation of user-supplied rotation plans."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings
from app.deps import settings_dep
from engine.rotation.models import RotationCropEntry, RotationPlan
from engine.rotation.plan_validation import validate_rotation_plan
from schemas.rotation import (
    RotationPlanInput,
    RotationPlanValidationIssue,
    RotationPlanValidationResponse,
    RotationPlanValidationResult,
)

router = APIRouter(prefix="/rotations", tags=["rotations"])
_SETTINGS_DEP = Depends(settings_dep)  # noqa: B008


@router.post(
    "/validate",
    response_model=RotationPlanValidationResponse,
    summary="Validate a user-supplied rotation plan structure",
    description=(
        "Checks crop identities and sequence positions only. It preserves the submitted "
        "entry order and allows repeated crops. Agronomic suitability is not assessed."
    ),
    responses={400: {"description": "Request failed schema validation"}},
)
def validate_plan(
    request: RotationPlanInput,
    settings: Settings = _SETTINGS_DEP,
) -> RotationPlanValidationResponse:
    """Adapt the wire contract to the pure engine and return its structural result."""
    plan = RotationPlan(
        entries=tuple(
            RotationCropEntry(
                sequence_position=entry.sequence_position,
                crop_id=entry.crop_id,
                crop_name=entry.crop_name,
            )
            for entry in request.entries
        )
    )
    result = validate_rotation_plan(plan)
    return RotationPlanValidationResponse(
        api_version=settings.api_version,
        data=RotationPlanValidationResult(
            structurally_valid=result.structurally_valid,
            issues=tuple(
                RotationPlanValidationIssue(
                    code=issue.code,
                    entry_index=issue.entry_index,
                    field=issue.field,
                    message=issue.message,
                )
                for issue in result.issues
            ),
            suitability_assessment=result.suitability_assessment,
        ),
    )
