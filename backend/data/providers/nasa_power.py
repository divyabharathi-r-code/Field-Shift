"""NASA POWER daily meteorology provider."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from data.cache import CacheError, JsonResponseCache
from data.providers.base import (
    DataQuery,
    Observation,
    ParameterMetadata,
    Provenance,
    ProviderResult,
)
from data.registry import NASA_POWER

NASA_POWER_ENDPOINT = NASA_POWER.access_url
LOGGER = logging.getLogger(__name__)
COMMUNITY = "AG"
TIME_STANDARD = "UTC"
POWER_PARAMETERS: tuple[str, ...] = ("PRECTOTCORR", "T2M_MAX", "T2M_MIN")
EXPECTED_UNITS: dict[str, str] = dict(NASA_POWER.units_by_parameter)

_LIMITATIONS = (
    "NASA POWER grid-cell data are regional context, not field-level measurements.",
    "Parameter-specific spatial resolution and licence terms are not yet verified.",
    "Dates are returned in UTC; no conversion to local civil time is applied.",
    "Missing values are represented as null and are not imputed.",
)


class PowerProviderError(RuntimeError):
    """Base class for NASA POWER provider failures."""


class PowerUnavailableError(PowerProviderError):
    """Raised when NASA POWER cannot be reached or offline data are unavailable."""


class PowerResponseError(PowerProviderError):
    """Raised when the NASA POWER response is invalid or inconsistent."""


class NasaPowerProvider:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        cache: JsonResponseCache | None = None,
        client: httpx.Client | None = None,
        endpoint: str = NASA_POWER_ENDPOINT,
    ) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")
        if not endpoint.startswith("https://"):
            raise ValueError("NASA POWER endpoint must use HTTPS")

        self.timeout_seconds = timeout_seconds
        default_cache_dir = Path(__file__).resolve().parents[1] / "cache" / "raw" / "NASA_POWER"
        self.cache = cache or JsonResponseCache(
            default_cache_dir,
            timedelta(days=NASA_POWER.cache_ttl_days),
        )
        self.client = client
        self.endpoint = endpoint

    def fetch(self, query: DataQuery, *, offline: bool = False) -> ProviderResult:
        request_params = self._request_params(query)
        cache_key = self._cache_key(request_params)
        cached = self.cache.load(cache_key)
        if cached is not None:
            return self._parse_response(query, cached.payload, cached.retrieved_at)
        if offline:
            raise PowerUnavailableError(
                "No unexpired NASA POWER response is available in the cache"
            )

        payload = self._request(request_params)
        retrieved_at = datetime.now(UTC)
        result = self._parse_response(query, payload, retrieved_at)
        try:
            self.cache.save(cache_key, payload, retrieved_at)
        except CacheError:
            LOGGER.warning(
                "NASA POWER response was valid but could not be persisted to cache",
                exc_info=True,
            )
        return result

    def _request_params(self, query: DataQuery) -> dict[str, str]:
        return {
            "parameters": ",".join(POWER_PARAMETERS),
            "community": COMMUNITY,
            "longitude": str(query.longitude),
            "latitude": str(query.latitude),
            "start": query.start_date.strftime("%Y%m%d"),
            "end": query.end_date.strftime("%Y%m%d"),
            "format": "JSON",
            "time-standard": TIME_STANDARD,
        }

    def _cache_key(self, params: dict[str, str]) -> str:
        canonical_request = json.dumps(
            {"endpoint": self.endpoint, "params": params},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()

    def _request(self, params: dict[str, str]) -> dict[str, Any]:
        try:
            if self.client is not None:
                response = self.client.get(
                    self.endpoint,
                    params=params,
                    timeout=self.timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.get(self.endpoint, params=params)
        except httpx.TimeoutException as exc:
            raise PowerUnavailableError("NASA POWER request timed out") from exc
        except httpx.RequestError as exc:
            raise PowerUnavailableError("NASA POWER request failed") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PowerUnavailableError(
                f"NASA POWER returned HTTP {exc.response.status_code}"
            ) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise PowerResponseError("NASA POWER returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise PowerResponseError("NASA POWER response must be a JSON object")
        return payload

    def _parse_response(
        self,
        query: DataQuery,
        payload: dict[str, Any],
        retrieved_at: datetime,
    ) -> ProviderResult:
        header = payload.get("header")
        parameters = payload.get("parameters")
        if not isinstance(header, dict) or not isinstance(parameters, dict):
            raise PowerResponseError(
                "NASA POWER response must include header and parameters objects"
            )
        if set(parameters) != set(POWER_PARAMETERS):
            raise PowerResponseError("NASA POWER response parameter names do not match the request")

        fill_value = self._finite_number(header.get("fill_value"), "header.fill_value")
        reported_latitude = self._coordinate(header.get("lat"), "header.lat", -90, 90)
        reported_longitude = self._coordinate(header.get("lon"), "header.lon", -180, 180)
        if reported_latitude != query.latitude:
            raise PowerResponseError(
                f"NASA POWER reported latitude {reported_latitude} does not match "
                f"requested latitude {query.latitude}"
            )
        if reported_longitude != query.longitude:
            raise PowerResponseError(
                f"NASA POWER reported longitude {reported_longitude} does not match "
                f"requested longitude {query.longitude}"
            )
        if header.get("time_standard") != TIME_STANDARD:
            raise PowerResponseError("NASA POWER response time standard is not UTC")
        returned_start = self._header_date(header.get("start"), "header.start")
        returned_end = self._header_date(header.get("end"), "header.end")
        if returned_start != query.start_date or returned_end != query.end_date:
            raise PowerResponseError("NASA POWER response date range does not match the request")

        source_names_raw = header.get("sources")
        if not isinstance(source_names_raw, list) or not source_names_raw or any(
            not isinstance(item, str) or not item for item in source_names_raw
        ):
            raise PowerResponseError("NASA POWER response source metadata is missing or invalid")

        metadata: list[tuple[str, ParameterMetadata]] = []
        values_by_parameter: dict[str, dict[date, float]] = {}
        returned_dates: set[date] = set()
        for parameter_name in POWER_PARAMETERS:
            parameter = parameters[parameter_name]
            if not isinstance(parameter, dict):
                raise PowerResponseError(f"Metadata for {parameter_name} must be an object")
            units = parameter.get("units")
            description = parameter.get("longname")
            if units != EXPECTED_UNITS[parameter_name]:
                raise PowerResponseError(
                    f"Unexpected units for {parameter_name}: "
                    f"expected {EXPECTED_UNITS[parameter_name]!r}"
                )
            if not isinstance(description, str) or not description.strip():
                raise PowerResponseError(f"Description for {parameter_name} is missing")
            data = parameter.get("data")
            if not isinstance(data, dict):
                raise PowerResponseError(f"Daily values for {parameter_name} must be an object")
            if not data:
                raise PowerResponseError(
                    f"NASA POWER returned an empty daily series for {parameter_name}"
                )

            parsed_values: dict[date, float] = {}
            for raw_date, raw_value in data.items():
                observation_date = self._data_date(raw_date, query)
                if isinstance(raw_value, bool):
                    raise PowerResponseError(f"Value for {parameter_name} on {raw_date} is invalid")
                value = self._finite_number(raw_value, f"{parameter_name}.{raw_date}")
                parsed_values[observation_date] = value
                returned_dates.add(observation_date)

            metadata.append((parameter_name, ParameterMetadata(units, description.strip())))
            values_by_parameter[parameter_name] = parsed_values

        if not returned_dates:
            raise PowerResponseError("NASA POWER response contains no daily dates")

        observations: list[Observation] = []
        current_date = query.start_date
        while current_date <= query.end_date:
            for parameter_name in POWER_PARAMETERS:
                raw_value = values_by_parameter[parameter_name].get(current_date)
                value = None if raw_value is None or raw_value == fill_value else raw_value
                observations.append(
                    Observation(
                        date=current_date,
                        parameter=parameter_name,
                        value=value,
                        units=EXPECTED_UNITS[parameter_name],
                        status="missing" if value is None else "ok",
                    )
                )
            current_date += timedelta(days=1)

        provenance = Provenance(
            source_id=NASA_POWER.source_id,
            source_type="PROVIDER_GRIDDED",
            provider=NASA_POWER.provider,
            product=NASA_POWER.product_or_dataset,
            endpoint=self.endpoint,
            retrieved_at=retrieved_at,
            latitude=query.latitude,
            longitude=query.longitude,
            reported_latitude=reported_latitude,
            reported_longitude=reported_longitude,
            requested_start_date=query.start_date,
            requested_end_date=query.end_date,
            returned_start_date=min(returned_dates),
            returned_end_date=max(returned_dates),
            time_standard=TIME_STANDARD,
            source_names=tuple(source_names_raw),
            parameters=POWER_PARAMETERS,
            parameter_metadata=tuple(metadata),
            limitations=_LIMITATIONS,
        )
        return ProviderResult(observations=tuple(observations), provenance=provenance)

    @staticmethod
    def _finite_number(value: object, field: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PowerResponseError(f"{field} must be a finite number")
        number = float(value)
        if not math.isfinite(number):
            raise PowerResponseError(f"{field} must be a finite number")
        return number

    @classmethod
    def _coordinate(cls, value: object, field: str, minimum: float, maximum: float) -> float:
        coordinate = cls._finite_number(value, field)
        if not minimum <= coordinate <= maximum:
            raise PowerResponseError(f"{field} is outside valid coordinate bounds")
        return coordinate

    @staticmethod
    def _header_date(value: object, field: str) -> date:
        if not isinstance(value, str) or re.fullmatch(r"\d{8}", value) is None:
            raise PowerResponseError(f"{field} must use YYYYMMDD format")
        try:
            return datetime.strptime(value, "%Y%m%d").date()
        except ValueError as exc:
            raise PowerResponseError(f"{field} is not a valid date") from exc

    @classmethod
    def _data_date(cls, value: object, query: DataQuery) -> date:
        observation_date = cls._header_date(value, "daily date")
        if not query.start_date <= observation_date <= query.end_date:
            raise PowerResponseError("NASA POWER returned a date outside the requested range")
        return observation_date
