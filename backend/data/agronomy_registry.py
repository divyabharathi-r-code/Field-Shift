"""Load and validate cited, curated Madurai agronomy evidence."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

ProductionSystem = Literal["IRRIGATED", "RAINFED", "UNKNOWN"]
EvidenceStatus = Literal["VERIFIED", "UNVERIFIED"]
TimeApplicability = Literal["HISTORICAL", "CURRENT", "UNKNOWN"]
EvidenceKind = Literal["PUBLISHED_STATISTIC", "PUBLISHED_DESCRIPTIVE_CLAIM"]
WindowStatus = Literal["KNOWN", "UNKNOWN"]

_PRODUCTION_SYSTEMS = {"IRRIGATED", "RAINFED", "UNKNOWN"}
_EVIDENCE_STATUSES = {"VERIFIED", "UNVERIFIED"}
_TIME_APPLICABILITIES = {"HISTORICAL", "CURRENT", "UNKNOWN"}
_EVIDENCE_KINDS = {"PUBLISHED_STATISTIC", "PUBLISHED_DESCRIPTIVE_CLAIM"}
_WINDOW_STATUSES = {"KNOWN", "UNKNOWN"}
_DATA_DIRECTORY = Path(__file__).resolve().parent / "curated"
_SOURCE_FIELDS = (
    "source_id",
    "provider",
    "title",
    "publication_year",
    "version",
    "url",
    "accessed_date",
    "geographic_scope",
    "source_kind",
    "verification_status",
    "time_applicability",
    "notes",
)
_TRAIT_FIELDS = (
    "record_id",
    "crop_id",
    "crop_name",
    "claim",
    "value",
    "unit",
    "source_id",
    "source_locator",
    "geographic_scope",
    "production_system_scope",
    "evidence_kind",
    "evidence_status",
    "time_applicability",
    "reference_period",
    "notes",
)
_CALENDAR_FIELDS = (
    "record_id",
    "crop_id",
    "crop_name",
    "season",
    "activity",
    "window_start",
    "window_end",
    "window_status",
    "timing_note",
    "source_id",
    "source_locator",
    "geographic_scope",
    "production_system_scope",
    "evidence_kind",
    "evidence_status",
    "time_applicability",
    "reference_period",
    "notes",
)


@dataclass(frozen=True)
class AgronomySource:
    source_id: str
    provider: str
    title: str
    publication_year: int | None
    version: str | None
    url: str
    accessed_date: date
    geographic_scope: str
    source_kind: str
    verification_status: EvidenceStatus
    time_applicability: TimeApplicability
    notes: str


@dataclass(frozen=True)
class CropTraitRecord:
    record_id: str
    crop_id: str
    crop_name: str
    claim: str
    value: str
    unit: str | None
    source_id: str
    source_locator: str
    geographic_scope: str
    production_system_scope: ProductionSystem
    evidence_kind: EvidenceKind
    evidence_status: EvidenceStatus
    time_applicability: TimeApplicability
    reference_period: str | None
    notes: str


@dataclass(frozen=True)
class CropCalendarRecord:
    record_id: str
    crop_id: str
    crop_name: str
    season: str
    activity: str
    window_start: date | None
    window_end: date | None
    window_status: WindowStatus
    timing_note: str | None
    source_id: str
    source_locator: str
    geographic_scope: str
    production_system_scope: ProductionSystem
    evidence_kind: EvidenceKind
    evidence_status: EvidenceStatus
    time_applicability: TimeApplicability
    reference_period: str | None
    notes: str


@dataclass(frozen=True)
class AgronomyRegistry:
    sources: tuple[AgronomySource, ...]
    crop_traits: tuple[CropTraitRecord, ...]
    crop_calendars: tuple[CropCalendarRecord, ...]


def load_agronomy_registry(
    *,
    sources_path: Path | None = None,
    crop_traits_path: Path | None = None,
    crop_calendars_path: Path | None = None,
) -> AgronomyRegistry:
    """Load the curated CSV files and reject malformed or uncited records."""
    source_rows = _read_csv(
        sources_path or _DATA_DIRECTORY / "agronomy_sources.csv",
        _SOURCE_FIELDS,
    )
    trait_rows = _read_csv(
        crop_traits_path or _DATA_DIRECTORY / "crop_traits.csv",
        _TRAIT_FIELDS,
    )
    calendar_rows = _read_csv(
        crop_calendars_path or _DATA_DIRECTORY / "crop_calendars.csv",
        _CALENDAR_FIELDS,
    )

    sources = tuple(_source_from_row(row, line) for line, row in source_rows)
    _unique_ids(
        ((source.source_id, line) for (line, _), source in zip(source_rows, sources, strict=True)),
        "source_id",
    )
    sources_by_id = {source.source_id: source for source in sources}
    traits = tuple(
        _trait_from_row(row, line, sources_by_id) for line, row in trait_rows
    )
    calendars = tuple(
        _calendar_from_row(row, line, sources_by_id) for line, row in calendar_rows
    )
    _unique_ids(
        [
            (record.record_id, line)
            for (line, _), record in zip(trait_rows, traits, strict=True)
        ]
        + [
            (record.record_id, line)
            for (line, _), record in zip(calendar_rows, calendars, strict=True)
        ],
        "record_id across claim files",
    )
    return AgronomyRegistry(sources, traits, calendars)


def _read_csv(path: Path, expected_fields: tuple[str, ...]) -> list[tuple[int, dict[str, str]]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file, strict=True)
            header = next(reader, None)
            if header is None:
                raise ValueError(f"{path.name}:1: missing CSV header")
            if len(header) != len(set(header)):
                raise ValueError(f"{path.name}:1: duplicate CSV headers {header}")
            if tuple(header) != expected_fields:
                raise ValueError(
                    f"{path.name}:1: expected CSV columns {expected_fields}, got {tuple(header)}"
                )
            rows: list[tuple[int, dict[str, str]]] = []
            for line, values in enumerate(reader, start=2):
                if len(values) != len(expected_fields):
                    shape = "missing" if len(values) < len(expected_fields) else "extra"
                    raise ValueError(
                        f"{path.name}:{line}: {shape} CSV columns; expected "
                        f"{len(expected_fields)}, got {len(values)}"
                    )
                rows.append(
                    (line, dict(zip(expected_fields, values, strict=True)))
                )
            return rows
    except csv.Error as exc:
        raise ValueError(
            f"{path.name}:line {reader.line_num}: malformed CSV: {exc}"
        ) from exc
    except OSError as exc:
        raise ValueError(f"Unable to read agronomy CSV {path}: {exc}") from exc


def _required(row: dict[str, str], field: str, path_line: str) -> str:
    value = row[field].strip()
    if not value:
        raise ValueError(f"{path_line}: {field} must not be blank")
    return value


def _choice(
    row: dict[str, str],
    field: str,
    allowed: set[str],
    path_line: str,
) -> str:
    value = _required(row, field, path_line)
    if value not in allowed:
        allowed_values = sorted(allowed)
        raise ValueError(
            f"{path_line}: invalid {field} {value!r}; expected one of {allowed_values}"
        )
    return value


def _date(value: str, field: str, path_line: str, *, required: bool) -> date | None:
    text = value.strip()
    if not text:
        if required:
            raise ValueError(f"{path_line}: {field} must not be blank")
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{path_line}: {field} must be an ISO date (YYYY-MM-DD)") from exc


def _source_from_row(row: dict[str, str], line: int) -> AgronomySource:
    path_line = f"agronomy_sources.csv:{line}"
    year_text = row["publication_year"].strip()
    publication_year = None
    if year_text:
        try:
            publication_year = int(year_text)
        except ValueError as exc:
            raise ValueError(f"{path_line}: publication_year must be a year") from exc
    accessed_date = _date(row["accessed_date"], "accessed_date", path_line, required=True)
    if accessed_date is None:
        raise ValueError(f"{path_line}: accessed_date must not be blank")
    return AgronomySource(
        source_id=_required(row, "source_id", path_line),
        provider=_required(row, "provider", path_line),
        title=_required(row, "title", path_line),
        publication_year=publication_year,
        version=row["version"].strip() or None,
        url=_required(row, "url", path_line),
        accessed_date=accessed_date,
        geographic_scope=_required(row, "geographic_scope", path_line),
        source_kind=_required(row, "source_kind", path_line),
        verification_status=_choice(
            row, "verification_status", _EVIDENCE_STATUSES, path_line
        ),  # type: ignore[assignment]
        time_applicability=_choice(
            row, "time_applicability", _TIME_APPLICABILITIES, path_line
        ),  # type: ignore[assignment]
        notes=row["notes"].strip(),
    )


def _validate_claim(
    row: dict[str, str],
    line: int,
    sources_by_id: dict[str, AgronomySource],
    filename: str,
) -> str:
    path_line = f"{filename}:{line}"
    claim_id = _required(row, "record_id", path_line)
    source_id = _required(row, "source_id", path_line)
    source = sources_by_id.get(source_id)
    if source is None:
        raise ValueError(f"{path_line}: unresolved source_id {source_id!r}")
    _required(row, "source_locator", path_line)
    _required(row, "geographic_scope", path_line)
    _choice(row, "production_system_scope", _PRODUCTION_SYSTEMS, path_line)
    _choice(row, "evidence_kind", _EVIDENCE_KINDS, path_line)
    evidence_status = _choice(row, "evidence_status", _EVIDENCE_STATUSES, path_line)
    if evidence_status == "VERIFIED" and source.verification_status == "UNVERIFIED":
        raise ValueError(
            f"{path_line}: VERIFIED claim {claim_id!r} references "
            f"UNVERIFIED source {source_id!r}"
        )
    _choice(row, "time_applicability", _TIME_APPLICABILITIES, path_line)
    return path_line


def _trait_from_row(
    row: dict[str, str],
    line: int,
    sources_by_id: dict[str, AgronomySource],
) -> CropTraitRecord:
    path_line = _validate_claim(row, line, sources_by_id, "crop_traits.csv")
    unit = row["unit"].strip() or None
    value = _required(row, "value", path_line)
    if unit in {"%", "percent"}:
        try:
            percentage = float(value)
        except ValueError as exc:
            raise ValueError(f"{path_line}: percentage value must be numeric") from exc
        if not 0 <= percentage <= 100:
            raise ValueError(f"{path_line}: percentage value must be between 0 and 100")
    return CropTraitRecord(
        record_id=_required(row, "record_id", path_line),
        crop_id=_required(row, "crop_id", path_line),
        crop_name=_required(row, "crop_name", path_line),
        claim=_required(row, "claim", path_line),
        value=value,
        unit=unit,
        source_id=row["source_id"].strip(),
        source_locator=row["source_locator"].strip(),
        geographic_scope=row["geographic_scope"].strip(),
        production_system_scope=row["production_system_scope"],  # type: ignore[assignment]
        evidence_kind=row["evidence_kind"],  # type: ignore[assignment]
        evidence_status=row["evidence_status"],  # type: ignore[assignment]
        time_applicability=row["time_applicability"],  # type: ignore[assignment]
        reference_period=row["reference_period"].strip() or None,
        notes=row["notes"].strip(),
    )


def _calendar_from_row(
    row: dict[str, str],
    line: int,
    sources_by_id: dict[str, AgronomySource],
) -> CropCalendarRecord:
    path_line = _validate_claim(row, line, sources_by_id, "crop_calendars.csv")
    window_status = _choice(row, "window_status", _WINDOW_STATUSES, path_line)
    window_start = _date(row["window_start"], "window_start", path_line, required=False)
    window_end = _date(row["window_end"], "window_end", path_line, required=False)
    if window_status == "UNKNOWN" and (window_start is not None or window_end is not None):
        raise ValueError(f"{path_line}: UNKNOWN window dates must be blank")
    if window_status == "KNOWN":
        if window_start is None or window_end is None:
            raise ValueError(f"{path_line}: KNOWN window requires both dates")
        if window_start > window_end:
            raise ValueError(f"{path_line}: window_start must not be after window_end")
    return CropCalendarRecord(
        record_id=_required(row, "record_id", path_line),
        crop_id=_required(row, "crop_id", path_line),
        crop_name=_required(row, "crop_name", path_line),
        season=_required(row, "season", path_line),
        activity=_required(row, "activity", path_line),
        window_start=window_start,
        window_end=window_end,
        window_status=window_status,  # type: ignore[assignment]
        timing_note=row["timing_note"].strip() or None,
        source_id=row["source_id"].strip(),
        source_locator=row["source_locator"].strip(),
        geographic_scope=row["geographic_scope"].strip(),
        production_system_scope=row["production_system_scope"],  # type: ignore[assignment]
        evidence_kind=row["evidence_kind"],  # type: ignore[assignment]
        evidence_status=row["evidence_status"],  # type: ignore[assignment]
        time_applicability=row["time_applicability"],  # type: ignore[assignment]
        reference_period=row["reference_period"].strip() or None,
        notes=row["notes"].strip(),
    )


def _unique_ids(records: Iterable[tuple[str, int]], field: str) -> set[str]:
    seen: set[str] = set()
    for record_id, line in records:
        if record_id in seen:
            raise ValueError(f"Duplicate {field} {record_id!r} at CSV row {line}")
        seen.add(record_id)
    return seen
