"""Deterministic structural validation; does not assess agronomic suitability."""

from __future__ import annotations

from engine.rotation.models import (
    PlanValidationIssue,
    PlanValidationResult,
    RotationCropEntry,
    RotationPlan,
)


def validate_rotation_plan(plan: RotationPlan) -> PlanValidationResult:
    """Validate identities and ordered positions without modifying the supplied plan."""
    issues: list[PlanValidationIssue] = []
    if not plan.entries:
        issues.append(
            PlanValidationIssue(
                code="INVALID_ENTRY",
                entry_index=None,
                field="entries",
                message="rotation plan must contain at least one crop entry",
            )
        )

    seen_positions: set[int] = set()
    for index, entry in enumerate(plan.entries):
        if not isinstance(entry, RotationCropEntry):
            issues.append(
                PlanValidationIssue(
                    code="INVALID_ENTRY",
                    entry_index=index,
                    field="entries",
                    message="entry must be a RotationCropEntry",
                )
            )
            continue

        position = entry.sequence_position
        if isinstance(position, bool) or not isinstance(position, int) or position < 1:
            issues.append(
                PlanValidationIssue(
                    code="INVALID_SEQUENCE_POSITION",
                    entry_index=index,
                    field="sequence_position",
                    message="sequence_position must be a positive integer",
                )
            )
        else:
            if position in seen_positions:
                issues.append(
                    PlanValidationIssue(
                        code="DUPLICATE_SEQUENCE_POSITION",
                        entry_index=index,
                        field="sequence_position",
                        message=f"sequence_position {position} is duplicated",
                    )
                )
            seen_positions.add(position)
            expected_position = index + 1
            if position != expected_position:
                issues.append(
                    PlanValidationIssue(
                        code="SEQUENCE_ORDER_MISMATCH",
                        entry_index=index,
                        field="sequence_position",
                        message=(
                            f"entry at index {index} must have sequence_position "
                            f"{expected_position}"
                        ),
                    )
                )

        has_crop_id = entry.crop_id is not None
        has_crop_name = entry.crop_name is not None
        if has_crop_id == has_crop_name:
            code = "AMBIGUOUS_CROP_IDENTITY" if has_crop_id else "MISSING_CROP_IDENTITY"
            message = (
                "provide exactly one of crop_id or crop_name"
                if has_crop_id
                else "a crop_id or crop_name is required"
            )
            issues.append(
                PlanValidationIssue(
                    code=code,
                    entry_index=index,
                    field="crop_id,crop_name",
                    message=message,
                )
            )
        else:
            identity = entry.crop_id if has_crop_id else entry.crop_name
            if not isinstance(identity, str) or not identity.strip():
                issues.append(
                    PlanValidationIssue(
                        code="BLANK_CROP_IDENTITY",
                        entry_index=index,
                        field="crop_id" if has_crop_id else "crop_name",
                        message="crop identity must be a nonblank string",
                    )
                )

    return PlanValidationResult(
        structurally_valid=not issues,
        issues=tuple(issues),
    )
