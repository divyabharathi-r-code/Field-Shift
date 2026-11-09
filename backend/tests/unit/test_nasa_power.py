"""Offline tests for the NASA POWER data provider."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from data.cache import CacheError, JsonResponseCache
from data.providers.base import DataQuery
from data.providers.nasa_power import (
    NASA_POWER_ENDPOINT,
    POWER_PARAMETERS,
    NasaPowerProvider,
    PowerResponseError,
    PowerUnavailableError,
)
from data.registry import NASA_POWER, SOURCE_REGISTRY

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "nasa_power_daily.json"
QUERY = DataQuery(
    latitude=12.34,
    longitude=-56.78,
    start_date=date(2020, 1, 1),
    end_date=date(2020, 1, 3),
)


def _fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _provider(
    tmp_path: Path,
    handler: httpx.MockTransport | None = None,
) -> tuple[NasaPowerProvider, httpx.Client | None]:
    client = httpx.Client(transport=handler) if handler is not None else None
    cache = JsonResponseCache(tmp_path / "cache", timedelta(days=7))
    return NasaPowerProvider(cache=cache, client=client), client


def test_request_parameters_and_normalized_observations(tmp_path: Path) -> None:
    captured: dict[str, str] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(200, json=_fixture_payload())

    provider, client = _provider(tmp_path, httpx.MockTransport(respond))
    assert client is not None
    try:
        result = provider.fetch(QUERY)
    finally:
        client.close()

    assert captured == {
        "parameters": ",".join(POWER_PARAMETERS),
        "community": "AG",
        "longitude": "-56.78",
        "latitude": "12.34",
        "start": "20200101",
        "end": "20200103",
        "format": "JSON",
        "time-standard": "UTC",
    }
    assert result.provenance.endpoint == NASA_POWER_ENDPOINT
    assert result.provenance.latitude == 12.34
    assert result.provenance.longitude == -56.78
    assert result.provenance.source_type == "PROVIDER_GRIDDED"
    assert result.provenance.time_standard == "UTC"
    assert result.provenance.source_names == ("MERRA2",)
    assert result.provenance.retrieved_at.tzinfo is not None
    assert "not field-level measurements" in result.provenance.limitations[0]
    assert result.provenance.returned_start_date == date(2020, 1, 1)
    assert result.provenance.returned_end_date == date(2020, 1, 3)
    assert len(result.observations) == 9
    assert result.observations[0].value == 1.25
    assert result.observations[0].units == "mm/day"
    assert result.observations[1].value == 24.5
    assert result.observations[2].value == 15.0
    precipitation_day_two = next(
        observation
        for observation in result.observations
        if observation.parameter == "PRECTOTCORR" and observation.date == date(2020, 1, 2)
    )
    missing_temperature_day_three = next(
        observation
        for observation in result.observations
        if observation.parameter == "T2M_MIN" and observation.date == date(2020, 1, 3)
    )
    assert precipitation_day_two.value is None
    assert precipitation_day_two.status == "missing"
    assert missing_temperature_day_three.value is None
    assert dict(result.provenance.parameter_metadata)["PRECTOTCORR"].description


def test_registry_keeps_unresolved_source_facts_unverified() -> None:
    assert SOURCE_REGISTRY["NASA_POWER"] is NASA_POWER
    assert NASA_POWER.source_type == "PROVIDER_GRIDDED"
    assert NASA_POWER.verification_status == "unverified"
    assert NASA_POWER.spatial_resolution is None
    assert NASA_POWER.licence is None
    assert NASA_POWER.authentication_required is None


def test_default_cache_ttl_comes_from_source_registry() -> None:
    provider = NasaPowerProvider()

    assert provider.cache.ttl == timedelta(days=NASA_POWER.cache_ttl_days)


def test_response_parameter_names_are_validated(tmp_path: Path) -> None:
    payload = _fixture_payload()
    payload["parameters"]["UNREQUESTED"] = payload["parameters"].pop("T2M_MIN")
    provider, client = _provider(
        tmp_path,
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    )
    assert client is not None
    try:
        with pytest.raises(PowerResponseError, match="parameter names"):
            provider.fetch(QUERY)
    finally:
        client.close()


@pytest.mark.parametrize(
    ("header_field", "reported_value", "message"),
    [
        ("lat", 12.35, "reported latitude.*requested latitude"),
        ("lon", -56.79, "reported longitude.*requested longitude"),
    ],
)
def test_response_coordinates_must_match_request(
    tmp_path: Path,
    header_field: str,
    reported_value: float,
    message: str,
) -> None:
    payload = _fixture_payload()
    payload["header"][header_field] = reported_value
    provider, client = _provider(
        tmp_path,
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    )
    assert client is not None
    try:
        with pytest.raises(PowerResponseError, match=message):
            provider.fetch(QUERY)
    finally:
        client.close()


@pytest.mark.parametrize("parameter_name", POWER_PARAMETERS)
def test_empty_parameter_series_is_rejected(
    tmp_path: Path,
    parameter_name: str,
) -> None:
    payload = _fixture_payload()
    payload["parameters"][parameter_name]["data"] = {}
    provider, client = _provider(
        tmp_path,
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    )
    assert client is not None
    try:
        with pytest.raises(PowerResponseError, match=f"empty daily series for {parameter_name}"):
            provider.fetch(QUERY)
    finally:
        client.close()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload["parameters"]["T2M_MAX"].update(units="K"), "Unexpected units"),
        (lambda payload: payload["header"].update(time_standard="LST"), "time standard"),
        (lambda payload: payload["header"].update(end="20200102"), "date range"),
        (
            lambda payload: payload["parameters"]["T2M_MAX"]["data"].update({"20200104": 20.0}),
            "outside the requested range",
        ),
    ],
)
def test_response_metadata_and_dates_are_validated(
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    payload = _fixture_payload()
    mutate(payload)
    provider, client = _provider(
        tmp_path,
        httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
    )
    assert client is not None
    try:
        with pytest.raises(PowerResponseError, match=message):
            provider.fetch(QUERY)
    finally:
        client.close()


def test_http_errors_and_timeouts_are_reported(tmp_path: Path) -> None:
    provider, client = _provider(
        tmp_path,
        httpx.MockTransport(lambda request: httpx.Response(503)),
    )
    assert client is not None
    try:
        with pytest.raises(PowerUnavailableError, match="HTTP 503"):
            provider.fetch(QUERY)
    finally:
        client.close()

    def time_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    timeout_provider, timeout_client = _provider(
        tmp_path / "timeout",
        httpx.MockTransport(time_out),
    )
    assert timeout_client is not None
    try:
        with pytest.raises(PowerUnavailableError, match="timed out"):
            timeout_provider.fetch(QUERY)
    finally:
        timeout_client.close()


def test_cache_prevents_repeat_requests_and_supports_offline_mode(tmp_path: Path) -> None:
    request_count = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json=_fixture_payload())

    provider, client = _provider(tmp_path, httpx.MockTransport(respond))
    assert client is not None
    try:
        online_result = provider.fetch(QUERY)
        cached_result = provider.fetch(QUERY, offline=True)
    finally:
        client.close()

    assert request_count == 1
    assert cached_result == online_result


def test_cache_write_failure_returns_valid_response_and_logs_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FailingSaveCache(JsonResponseCache):
        def save(self, key: str, payload: dict[str, Any], retrieved_at: Any) -> None:
            raise CacheError("simulated disk write failure")

    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=_fixture_payload())
        )
    )
    provider = NasaPowerProvider(
        cache=FailingSaveCache(tmp_path / "cache", timedelta(days=7)),
        client=client,
    )
    try:
        result = provider.fetch(QUERY)
    finally:
        client.close()

    assert len(result.observations) == 9
    assert "could not be persisted to cache" in caplog.text
    assert "simulated disk write failure" in caplog.text


def test_cache_write_failure_does_not_hide_response_validation_errors(
    tmp_path: Path,
) -> None:
    class FailingSaveCache(JsonResponseCache):
        def save(self, key: str, payload: dict[str, Any], retrieved_at: Any) -> None:
            raise CacheError("simulated disk write failure")

    payload = _fixture_payload()
    payload["parameters"]["T2M_MAX"]["units"] = "K"
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )
    provider = NasaPowerProvider(
        cache=FailingSaveCache(tmp_path / "cache", timedelta(days=7)),
        client=client,
    )
    try:
        with pytest.raises(PowerResponseError, match="Unexpected units"):
            provider.fetch(QUERY)
    finally:
        client.close()


def test_offline_cache_miss_is_explicit(tmp_path: Path) -> None:
    provider = NasaPowerProvider(
        cache=JsonResponseCache(tmp_path / "empty", timedelta(days=7))
    )
    with pytest.raises(PowerUnavailableError, match="cache"):
        provider.fetch(QUERY, offline=True)


@pytest.mark.parametrize(
    ("latitude", "longitude", "start_date", "end_date"),
    [
        (91, 0, date(2020, 1, 1), date(2020, 1, 2)),
        (0, 181, date(2020, 1, 1), date(2020, 1, 2)),
        (float("nan"), 0, date(2020, 1, 1), date(2020, 1, 2)),
        (0, 0, date(2020, 1, 2), date(2020, 1, 1)),
    ],
)
def test_query_coordinates_and_dates_are_validated(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> None:
    with pytest.raises(ValueError):
        DataQuery(latitude, longitude, start_date, end_date)
