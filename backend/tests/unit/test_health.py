"""Phase 1 gate tests for GET /api/v1/health (docs/07 M1).

Checks:
  1. exact required payload   {"status":"ok","service":"fieldshift"}
  2. success-envelope shape   (docs/03 §0.1)
  3. OpenAPI served at /openapi.json and includes the health route
"""

from __future__ import annotations

from fastapi.testclient import TestClient

HEALTH_URL = "/api/v1/health"


def test_health_returns_exact_required_payload(client: TestClient) -> None:
    resp = client.get(HEALTH_URL)
    assert resp.status_code == 200
    body = resp.json()
    # The Phase-1 requirement, verbatim, inside the envelope's data block.
    assert {"status": "ok", "service": "fieldshift"}.items() <= body["data"].items()


def test_health_envelope_has_contract_fields(client: TestClient) -> None:
    body = client.get(HEALTH_URL).json()
    assert body["api_version"] == "v1"
    assert body["engine_version"] == "0.1.0"
    # docs/03 §1 readiness extras
    assert body["data"]["offline_mode"] is True
    assert body["data"]["cache_warm"] is False
    # No source may be advertised before Phase 2 verifies it.
    assert body["data"]["sources_available"] == []
    assert isinstance(body["provenance"], list)
    assert isinstance(body["warnings"], list)
    assert body["confidence"]["level"] == "unknown"


def test_openapi_json_served_and_contains_health(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert spec["info"]["title"] == "FieldShift API"
    assert HEALTH_URL in spec["paths"]


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "NOT_FOUND"
    assert "message" in err and "details" in err and "warnings" in err
