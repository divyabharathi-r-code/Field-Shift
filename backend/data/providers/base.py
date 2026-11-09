"""Shared types for external data providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Protocol

ObservationStatus = Literal["ok", "missing"]
SourceType = Literal["PROVIDER_GRIDDED"]


@dataclass(frozen=True)
class DataQuery:
    latitude: float
    longitude: float
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        if isinstance(self.latitude, bool) or not isinstance(self.latitude, (int, float)):
            raise ValueError("latitude must be a finite number")
        if isinstance(self.longitude, bool) or not isinstance(self.longitude, (int, float)):
            raise ValueError("longitude must be a finite number")
        if not (-90 <= self.latitude <= 90):
            raise ValueError("latitude must be between -90 and 90")
        if not (-180 <= self.longitude <= 180):
            raise ValueError("longitude must be between -180 and 180")
        if not isinstance(self.start_date, date) or isinstance(self.start_date, datetime):
            raise ValueError("start_date must be a date")
        if not isinstance(self.end_date, date) or isinstance(self.end_date, datetime):
            raise ValueError("end_date must be a date")
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")


@dataclass(frozen=True)
class Observation:
    date: date
    parameter: str
    value: float | None
    units: str
    status: ObservationStatus


@dataclass(frozen=True)
class ParameterMetadata:
    units: str
    description: str


@dataclass(frozen=True)
class Provenance:
    source_id: str
    source_type: SourceType
    provider: str
    product: str
    endpoint: str
    retrieved_at: datetime
    latitude: float
    longitude: float
    reported_latitude: float
    reported_longitude: float
    requested_start_date: date
    requested_end_date: date
    returned_start_date: date
    returned_end_date: date
    time_standard: str
    source_names: tuple[str, ...]
    parameters: tuple[str, ...]
    parameter_metadata: tuple[tuple[str, ParameterMetadata], ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ProviderResult:
    observations: tuple[Observation, ...]
    provenance: Provenance


class Provider(Protocol):
    def fetch(self, query: DataQuery, *, offline: bool = False) -> ProviderResult:
        """Return observations and source provenance for a query."""
