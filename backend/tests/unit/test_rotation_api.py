"""Offline tests for the rotation-plan structural validation API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

ROTATION_VALIDATE_URL = "/api/v1/rotations/validate"


def test_validate_rotation_plan_returns_structural_result_and_allows_repeated_crops(
    client: TestClient,
) -> None:
    response = client.post(
        ROTATION_VALIDATE_URL,
        json={
            "entries": [
                {"sequence_position": 1, "crop_id": "crop-a"},
                {"sequence_position": 2, "crop_name": "User crop"},
                {"sequence_position": 3, "crop_id": "crop-a"},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["data"] == {
        "structurally_valid": True,
        "issues": [],
        "suitability_assessment": "NOT_ASSESSED",
    }


def test_validate_rotation_plan_returns_ordered_machine_readable_issues(
    client: TestClient,
) -> None:
    response = client.post(
        ROTATION_VALIDATE_URL,
        json={
            "entries": [
                {"sequence_position": 2, "crop_id": "crop-b"},
                {"sequence_position": 1, "crop_id": "crop-a"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["structurally_valid"] is False
    assert [issue["code"] for issue in data["issues"]] == [
        "SEQUENCE_ORDER_MISMATCH",
        "SEQUENCE_ORDER_MISMATCH",
    ]
    assert [issue["entry_index"] for issue in data["issues"]] == [0, 1]
    assert data["suitability_assessment"] == "NOT_ASSESSED"


def test_validate_rotation_plan_reports_duplicate_positions(client: TestClient) -> None:
    response = client.post(
        ROTATION_VALIDATE_URL,
        json={
            "entries": [
                {"sequence_position": 1, "crop_id": "crop-a"},
                {"sequence_position": 1, "crop_id": "crop-b"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["structurally_valid"] is False
    assert [issue["code"] for issue in data["issues"]] == [
        "DUPLICATE_SEQUENCE_POSITION",
        "SEQUENCE_ORDER_MISMATCH",
    ]
    assert [issue["entry_index"] for issue in data["issues"]] == [1, 1]


def test_invalid_rotation_request_uses_standard_validation_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.post(ROTATION_VALIDATE_URL, json={"entries": []})

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "Request body/query failed schema validation."


def test_openapi_documents_rotation_validation_endpoint(client: TestClient) -> None:
    operation = client.get("/openapi.json").json()["paths"][ROTATION_VALIDATE_URL]["post"]

    assert operation["summary"] == "Validate a user-supplied rotation plan structure"
    assert "Agronomic suitability is not assessed." in operation["description"]
