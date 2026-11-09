"""Offline tests for the experimental NASA POWER environmental API."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.deps import nasa_power_provider_dep, settings_dep
from app.main import create_app
from data.cache import CacheError
from data.providers.base import (
    DataQuery,
    Observation,
    ParameterMetadata,
    Provenance,
    ProviderResult,
)
from data.providers.nasa_power import (
    PowerResponseError,
    PowerUnavailableError,
)
from data.registry import NASA_POWER

DAILY_URL = "/api/v1/environmental/daily"


def _result() -> ProviderResult:
    query = DataQuery(
        latitude=9.9252,
        longitude=78.1198,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 2),
    )
    return ProviderResult(
        observations=(
            Observation(date(2020, 1, 1), "PRECTOTCORR", 1.25, "mm/day", "ok"),
            Observation(date(2020, 1, 1), "T2M_MAX", 28.0, "C", "ok"),
            Observation(date(2020, 1, 1), "T2M_MIN", 19.0, "C", "ok"),
            Observation(date(2020, 1, 2), "PRECTOTCORR", None, "mm/day", "missing"),
            Observation(date(2020, 1, 2), "T2M_MAX", 29.0, "C", "ok"),
            Observation(date(2020, 1, 2), "T2M_MIN", 20.0, "C", "ok"),
        ),
        provenance=Provenance(
            source_id="NASA_POWER",
            source_type="PROVIDER_GRIDDED",
            provider="NASA POWER",
            product="POWER Daily Point meteorology",
            endpoint=NASA_POWER.access_url,
            retrieved_at=datetime(2026, 11, 9, tzinfo=UTC),
            latitude=query.latitude,
            longitude=query.longitude,
            reported_latitude=query.latitude,
            reported_longitude=query.longitude,
            requested_start_date=query.start_date,
            requested_end_date=query.end_date,
            returned_start_date=query.start_date,
            returned_end_date=query.end_date,
            time_standard="UTC",
            source_names=("MERRA2",),
            parameters=("PRECTOTCORR", "T2M_MAX", "T2M_MIN"),
            parameter_metadata=(
                ("PRECTOTCORR", ParameterMetadata("mm/day", "Precipitation")),
                ("T2M_MAX", ParameterMetadata("C", "Maximum temperature")),
                ("T2M_MIN", ParameterMetadata("C", "Minimum temperature")),
            ),
            limitations=("Regional context, not field-level measurements.",),
        ),
    )


class FakeProvider:
    def __init__(
        self,
        result: ProviderResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or _result()
        self.error = error
        self.calls: list[tuple[DataQuery, bool]] = []

    def fetch(self, query: DataQuery, *, offline: bool = False) -> ProviderResult:
        self.calls.append((query, offline))
        if self.error is not None:
            raise self.error
        return self.result


def _client(
    *,
    enabled: bool = True,
    offline: bool = False,
    provider: FakeProvider | None = None,
) -> tuple[TestClient, FakeProvider | None]:
    app = create_app()
    app.dependency_overrides[settings_dep] = lambda: Settings(
        nasa_power_enabled=enabled,
        offline_mode=offline,
    )
    if provider is not None:
        app.dependency_overrides[nasa_power_provider_dep] = lambda: provider
    return TestClient(app), provider


def test_nasa_power_feature_flag_defaults_to_disabled() -> None:
    assert Settings().nasa_power_enabled is False


def test_disabled_source_returns_503_without_provider_construction_or_fetch(monkeypatch) -> None:
    app = create_app()
    app.dependency_overrides[settings_dep] = lambda: Settings(nasa_power_enabled=False)
    provider = FakeProvider()
    constructor_calls = []

    def track_construction():
        constructor_calls.append(True)
        return provider

    monkeypatch.setattr("app.deps.NasaPowerProvider", track_construction)

    response = TestClient(app).get(
        DAILY_URL,
        params={
            "latitude": 9.9252,
            "longitude": 78.1198,
            "start_date": "2020-01-01",
            "end_date": "2020-01-02",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SOURCE_DISABLED"
    assert constructor_calls == []
    assert provider.calls == []


@pytest.mark.parametrize(
    "params",
    [
        {
            "latitude": 91,
            "longitude": 78,
            "start_date": "2020-01-01",
            "end_date": "2020-01-02",
        },
        {
            "latitude": 9,
            "longitude": 78,
            "start_date": "2020-01-03",
            "end_date": "2020-01-02",
        },
    ],
    ids=["invalid-coordinates", "reversed-date-range"],
)
def test_disabled_source_still_validates_request_before_gate(
    params: dict[str, object],
) -> None:
    client, _ = _client(enabled=False)

    response = client.get(DAILY_URL, params=params)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_daily_endpoint_returns_standard_envelope_and_full_provenance() -> None:
    provider = FakeProvider()
    client, _ = _client(provider=provider)

    response = client.get(
        DAILY_URL,
        params={
            "latitude": 9.9252,
            "longitude": 78.1198,
            "start_date": "2020-01-01",
            "end_date": "2020-01-02",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert {"data", "provenance", "warnings", "confidence"} <= body.keys()
    assert body["data"]["experimental"] is True
    assert body["data"]["source_verification_status"] == "unverified"
    assert len(body["data"]["observations"]) == 6
    missing = body["data"]["observations"][3]
    assert missing["value"] is None
    assert missing["status"] == "missing"

    provenance = body["provenance"][0]
    assert provenance["source_type"] == "PROVIDER_GRIDDED"
    assert provenance["source_id"] == "NASA_POWER"
    assert provenance["latitude"] == provenance["reported_latitude"] == 9.9252
    assert provenance["longitude"] == provenance["reported_longitude"] == 78.1198
    assert provenance["requested_start_date"] == "2020-01-01"
    assert provenance["requested_end_date"] == "2020-01-02"
    assert provenance["time_standard"] == "UTC"
    assert provenance["source_names"] == ["MERRA2"]
    assert [item["parameter"] for item in provenance["parameter_metadata"]] == [
        "PRECTOTCORR",
        "T2M_MAX",
        "T2M_MIN",
    ]
    assert provenance["limitations"] == ["Regional context, not field-level measurements."]
    assert provider is not None
    assert provider.calls[0][0] == DataQuery(
        latitude=9.9252,
        longitude=78.1198,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 2),
    )


@pytest.mark.parametrize(
    ("params", "error_path"),
    [
        (
            {
                "latitude": 91,
                "longitude": 78,
                "start_date": "2020-01-01",
                "end_date": "2020-01-02",
            },
            "latitude",
        ),
        (
            {
                "latitude": 9,
                "longitude": 78,
                "start_date": "2020-01-03",
                "end_date": "2020-01-02",
            },
            "start_date",
        ),
    ],
)
def test_invalid_query_uses_existing_400_validation_convention(
    params: dict[str, object],
    error_path: str,
) -> None:
    client, _ = _client(provider=FakeProvider())

    response = client.get(DAILY_URL, params=params)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert error_path in str(response.json()["error"]["details"])


@pytest.mark.parametrize(
    ("provider_error", "status_code", "error_code"),
    [
        (PowerUnavailableError("cache miss"), 503, "PROVIDER_UNAVAILABLE"),
        (PowerResponseError("bad response"), 502, "UPSTREAM_INVALID_RESPONSE"),
        (CacheError("corrupt cache"), 500, "CACHE_ERROR"),
    ],
)
def test_provider_failures_use_approved_error_mappings(
    provider_error: Exception,
    status_code: int,
    error_code: str,
) -> None:
    client, _ = _client(provider=FakeProvider(error=provider_error))

    response = client.get(
        DAILY_URL,
        params={
            "latitude": 9.9252,
            "longitude": 78.1198,
            "start_date": "2020-01-01",
            "end_date": "2020-01-02",
        },
    )

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == error_code


def test_offline_setting_is_forwarded_to_provider() -> None:
    provider = FakeProvider()
    client, _ = _client(provider=provider, offline=True)

    response = client.get(
        DAILY_URL,
        params={
            "latitude": 9.9252,
            "longitude": 78.1198,
            "start_date": "2020-01-01",
            "end_date": "2020-01-02",
        },
    )

    assert response.status_code == 200
    assert provider.calls[0][1] is True


def test_offline_cache_miss_returns_unavailable_without_network_access() -> None:
    provider = FakeProvider(error=PowerUnavailableError("No unexpired cache entry"))
    client, _ = _client(provider=provider, offline=True)

    response = client.get(
        DAILY_URL,
        params={
            "latitude": 9.9252,
            "longitude": 78.1198,
            "start_date": "2020-01-01",
            "end_date": "2020-01-02",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert provider.calls[0][1] is True


def test_health_and_agronomy_endpoints_remain_available() -> None:
    client, _ = _client(enabled=False)

    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/knowledge/agronomy").status_code == 200


def test_openapi_documents_environmental_endpoint() -> None:
    client, _ = _client(provider=FakeProvider())

    operation = client.get("/openapi.json").json()["paths"][DAILY_URL]["get"]

    assert operation["summary"] == "Get experimental NASA POWER daily data"
    assert "inclusive date range" in operation["description"]
    assert {400, 500, 502, 503} <= {int(code) for code in operation["responses"]}
