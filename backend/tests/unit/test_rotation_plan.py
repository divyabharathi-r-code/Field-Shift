"""Tests for the user-supplied rotation-plan contract and pure validation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from engine.rotation.models import RotationCropEntry, RotationPlan
from engine.rotation.plan_validation import validate_rotation_plan
from schemas.rotation import RotationPlanInput


def _plan(*entries: tuple[int, str]) -> RotationPlan:
    return RotationPlan(
        entries=tuple(
            RotationCropEntry(sequence_position=position, crop_id=crop_id)
            for position, crop_id in entries
        )
    )


def test_valid_plan_preserves_user_supplied_order() -> None:
    request = RotationPlanInput.model_validate(
        {
            "entries": [
                {"sequence_position": 1, "crop_id": "crop-z"},
                {"sequence_position": 2, "crop_name": "User crop"},
                {"sequence_position": 3, "crop_id": "crop-a"},
            ]
        }
    )
    result = validate_rotation_plan(
        RotationPlan(
            entries=tuple(
                RotationCropEntry(
                    sequence_position=entry.sequence_position,
                    crop_id=entry.crop_id,
                    crop_name=entry.crop_name,
                )
                for entry in request.entries
            )
        )
    )

    assert result.structurally_valid is True
    assert result.issues == ()
    assert result.suitability_assessment == "NOT_ASSESSED"
    assert [entry.crop_id or entry.crop_name for entry in request.entries] == [
        "crop-z",
        "User crop",
        "crop-a",
    ]


def test_single_entry_plan_is_structurally_valid() -> None:
    assert validate_rotation_plan(_plan((1, "user-crop"))).structurally_valid


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"entries": []},
        {"entries": [{"sequence_position": 1}]},
        {"entries": [{"sequence_position": 1, "crop_id": "id", "crop_name": "name"}]},
        {"entries": [{"sequence_position": True, "crop_id": "id"}]},
        {"entries": [{"sequence_position": 1, "crop_id": "   "}]},
        {"entries": [{"sequence_position": 1, "crop_name": " \t"}]},
        {"entries": [{"sequence_position": 1, "crop_id": "id", "planting_date": "2026-06-01"}]},
        {"entries": [{"sequence_position": 1, "crop_id": "id"}, {"crop_id": "missing-position"}]},
    ],
)
def test_invalid_or_incomplete_contract_data_is_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RotationPlanInput.model_validate(payload)


def test_duplicate_sequence_positions_are_reported() -> None:
    result = validate_rotation_plan(_plan((1, "crop-a"), (1, "crop-b")))

    assert result.structurally_valid is False
    assert [issue.code for issue in result.issues] == [
        "DUPLICATE_SEQUENCE_POSITION",
        "SEQUENCE_ORDER_MISMATCH",
    ]


def test_schema_parse_does_not_claim_structural_validity_for_duplicate_positions() -> None:
    request = RotationPlanInput.model_validate(
        {
            "entries": [
                {"sequence_position": 1, "crop_id": "crop-a"},
                {"sequence_position": 1, "crop_id": "crop-b"},
            ]
        }
    )
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

    assert len(request.entries) == 2
    assert result.structurally_valid is False
    assert "DUPLICATE_SEQUENCE_POSITION" in [issue.code for issue in result.issues]


def test_out_of_order_positions_are_reported_without_reordering_entries() -> None:
    plan = _plan((2, "crop-b"), (1, "crop-a"))
    result = validate_rotation_plan(plan)

    assert result.structurally_valid is False
    assert [issue.code for issue in result.issues] == [
        "SEQUENCE_ORDER_MISMATCH",
        "SEQUENCE_ORDER_MISMATCH",
    ]
    assert [entry.crop_id for entry in plan.entries] == ["crop-b", "crop-a"]


def test_repeated_crop_identity_is_allowed() -> None:
    repeated_ids = validate_rotation_plan(
        _plan((1, "same-crop"), (2, "same-crop"))
    )
    repeated_names = RotationPlanInput.model_validate(
        {
            "entries": [
                {"sequence_position": 1, "crop_name": "Same crop"},
                {"sequence_position": 2, "crop_name": "Same crop"},
            ]
        }
    )

    assert repeated_ids.structurally_valid is True
    assert repeated_ids.issues == ()
    assert len(repeated_names.entries) == 2


def test_validation_is_deterministic() -> None:
    plan = _plan((1, "crop-a"), (3, "crop-c"))

    assert validate_rotation_plan(plan) == validate_rotation_plan(plan)


def test_validation_does_not_mutate_input() -> None:
    entries = (
        RotationCropEntry(sequence_position=1, crop_id="crop-a"),
        RotationCropEntry(sequence_position=2, crop_name="Crop B"),
    )
    plan = RotationPlan(entries=entries)

    validate_rotation_plan(plan)

    assert plan.entries == entries
    with pytest.raises(FrozenInstanceError):
        entries[0].sequence_position = 2  # type: ignore[misc]


def test_plan_copies_mutable_entry_collection_to_immutable_tuple() -> None:
    entries = [RotationCropEntry(sequence_position=1, crop_id="crop-a")]
    plan = RotationPlan(entries=entries)  # type: ignore[arg-type]

    entries.append(RotationCropEntry(sequence_position=2, crop_id="crop-b"))

    assert len(plan.entries) == 1
    assert plan.entries[0].crop_id == "crop-a"
    assert isinstance(plan.entries, tuple)
    with pytest.raises(AttributeError):
        plan.entries.append(RotationCropEntry(sequence_position=2, crop_id="crop-b"))  # type: ignore[attr-defined]


def test_plan_accepts_tuple_entries() -> None:
    entries = (RotationCropEntry(sequence_position=1, crop_id="crop-a"),)

    plan = RotationPlan(entries=entries)

    assert plan.entries == entries
    assert plan.entries is entries


def test_plan_rejects_unordered_set_entries() -> None:
    entries = {RotationCropEntry(sequence_position=1, crop_id="crop-a")}

    with pytest.raises(
        TypeError,
        match="^RotationPlan\\.entries must be a list or tuple$",
    ):
        RotationPlan(entries=entries)  # type: ignore[arg-type]


def test_schema_does_not_mutate_caller_payload() -> None:
    payload = {
        "entries": [
            {"sequence_position": 1, "crop_name": "  Crop A  "},
            {"sequence_position": 2, "crop_id": "crop-b"},
        ]
    }
    original_payload = {
        "entries": [dict(entry) for entry in payload["entries"]]
    }

    plan = RotationPlanInput.model_validate(payload)

    assert payload == original_payload
    assert [entry.crop_name or entry.crop_id for entry in plan.entries] == [
        "Crop A",
        "crop-b",
    ]


def test_engine_reports_missing_identity_without_inference() -> None:
    result = validate_rotation_plan(
        RotationPlan(entries=(RotationCropEntry(sequence_position=1),))
    )

    assert result.structurally_valid is False
    assert result.issues[0].code == "MISSING_CROP_IDENTITY"
    assert result.suitability_assessment == "NOT_ASSESSED"


def test_engine_directly_reports_empty_plan() -> None:
    result = validate_rotation_plan(RotationPlan(entries=()))

    assert result.structurally_valid is False
    assert len(result.issues) == 1
    assert result.issues[0].code == "INVALID_ENTRY"
    assert result.issues[0].field == "entries"


@pytest.mark.parametrize(
    ("entry", "expected_code"),
    [
        (RotationCropEntry(sequence_position=1, crop_id="  "), "BLANK_CROP_IDENTITY"),
        (RotationCropEntry(sequence_position=1, crop_name="\t"), "BLANK_CROP_IDENTITY"),
        (object(), "INVALID_ENTRY"),
    ],
)
def test_engine_reports_blank_identity_and_malformed_runtime_entry(
    entry: object,
    expected_code: str,
) -> None:
    plan = RotationPlan(entries=(entry,))  # type: ignore[arg-type]

    result = validate_rotation_plan(plan)

    assert result.structurally_valid is False
    assert result.issues[0].code == expected_code
