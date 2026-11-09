"""Offline tests for the read-only agronomy knowledge API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.deps import agronomy_registry_dep
from app.main import create_app
from data.agronomy_registry import load_agronomy_registry

AGRONOMY_URL = "/api/v1/knowledge/agronomy"


def test_agronomy_endpoint_returns_curated_record_counts(client: TestClient) -> None:
    response = client.get(AGRONOMY_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert len(body["data"]["sources"]) == 3
    assert len(body["data"]["crop_traits"]) == 24
    assert len(body["data"]["crop_calendars"]) == 5
    assert "not farm-level observations" in body["data"]["scope_notice"]


def test_agronomy_endpoint_preserves_source_claim_linkage_and_scope(
    client: TestClient,
) -> None:
    body = client.get(AGRONOMY_URL).json()["data"]
    sources_by_id = {source["source_id"]: source for source in body["sources"]}

    for claim in [*body["crop_traits"], *body["crop_calendars"]]:
        assert claim["source_id"] in sources_by_id
        assert claim["source_locator"]
        assert claim["geographic_scope"]
        assert claim["production_system_scope"] in {"IRRIGATED", "RAINFED", "UNKNOWN"}
        assert claim["evidence_kind"] in {
            "PUBLISHED_STATISTIC",
            "PUBLISHED_DESCRIPTIVE_CLAIM",
        }
        assert claim["evidence_status"] in {"VERIFIED", "UNVERIFIED"}
        assert claim["time_applicability"] in {"HISTORICAL", "CURRENT", "UNKNOWN"}

    cotton_rainfed = next(
        claim
        for claim in body["crop_traits"]
        if claim["record_id"] == "DAP_COTTON_RAINFED_SHARE"
    )
    assert cotton_rainfed["value"] == "77"
    assert cotton_rainfed["geographic_scope"] == "Madurai district"
    assert cotton_rainfed["time_applicability"] == "HISTORICAL"
    assert "individual farm" in cotton_rainfed["notes"]


def test_agronomy_endpoint_preserves_unknown_calendar_dates(client: TestClient) -> None:
    calendars = client.get(AGRONOMY_URL).json()["data"]["crop_calendars"]

    assert all(calendar["window_status"] == "UNKNOWN" for calendar in calendars)
    assert all(calendar["window_start"] is None for calendar in calendars)
    assert all(calendar["window_end"] is None for calendar in calendars)


def test_invalid_agronomy_registry_returns_controlled_error(
    monkeypatch,
) -> None:
    def invalid_registry():
        raise ValueError("crop_traits.csv:2: unresolved source_id")

    monkeypatch.setattr("app.deps.load_agronomy_registry", invalid_registry)
    app = create_app()
    client = TestClient(app)

    response = client.get(AGRONOMY_URL)

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "KNOWLEDGE_DATA_INVALID"
    assert error["message"] == "Curated agronomy evidence could not be loaded."
    assert "crop_traits.csv:2" in error["details"]["details"]["reason"]


def test_endpoint_uses_registry_dependency_override() -> None:
    registry = load_agronomy_registry()
    app = create_app()
    app.dependency_overrides[agronomy_registry_dep] = lambda: registry

    response = TestClient(app).get(AGRONOMY_URL)

    assert response.status_code == 200
    assert len(response.json()["data"]["sources"]) == len(registry.sources)
