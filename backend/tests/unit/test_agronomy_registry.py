"""Offline tests for the curated agronomy evidence registry."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from data.agronomy_registry import load_agronomy_registry

DATA_DIRECTORY = Path(__file__).parents[2] / "data" / "curated"
SOURCE_FIELDS = (
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
TRAIT_FIELDS = (
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
CALENDAR_FIELDS = (
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


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_csv_rows(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        csv.writer(file).writerows(rows)


def _source() -> dict[str, str]:
    return {
        "source_id": "SOURCE_A",
        "provider": "TNAU",
        "title": "Verified source",
        "publication_year": "2017",
        "version": "2017-18",
        "url": "https://example.test/source",
        "accessed_date": "2026-11-09",
        "geographic_scope": "Madurai district",
        "source_kind": "government_district_plan",
        "verification_status": "VERIFIED",
        "time_applicability": "HISTORICAL",
        "notes": "",
    }


def _trait() -> dict[str, str]:
    return {
        "record_id": "TRAIT_A",
        "crop_id": "cotton",
        "crop_name": "Cotton",
        "claim": "reported_area_share",
        "value": "77",
        "unit": "percent",
        "source_id": "SOURCE_A",
        "source_locator": "printed p.93, §4.1.4.1",
        "geographic_scope": "Madurai district",
        "production_system_scope": "RAINFED",
        "evidence_kind": "PUBLISHED_STATISTIC",
        "evidence_status": "VERIFIED",
        "time_applicability": "HISTORICAL",
        "reference_period": "Not stated in cited passage",
        "notes": "District aggregate, not a farm-level status.",
    }


def _calendar() -> dict[str, str]:
    return {
        "record_id": "CALENDAR_A",
        "crop_id": "paddy",
        "crop_name": "Paddy",
        "season": "Kuruvai",
        "activity": "cultivation season",
        "window_start": "",
        "window_end": "",
        "window_status": "UNKNOWN",
        "timing_note": "",
        "source_id": "SOURCE_A",
        "source_locator": "printed p.81, §4.1.1.1",
        "geographic_scope": "Madurai district",
        "production_system_scope": "UNKNOWN",
        "evidence_kind": "PUBLISHED_DESCRIPTIVE_CLAIM",
        "evidence_status": "VERIFIED",
        "time_applicability": "HISTORICAL",
        "reference_period": "Not stated in cited passage",
        "notes": "Season name only; exact dates are not supplied.",
    }


def _load_temp_registry(
    tmp_path: Path,
    *,
    source_rows: list[dict[str, str]] | None = None,
    trait_rows: list[dict[str, str]] | None = None,
    calendar_rows: list[dict[str, str]] | None = None,
):
    sources_path, traits_path, calendars_path = _write_temp_registry_files(
        tmp_path,
        source_rows=source_rows,
        trait_rows=trait_rows,
        calendar_rows=calendar_rows,
    )
    return load_agronomy_registry(
        sources_path=sources_path,
        crop_traits_path=traits_path,
        crop_calendars_path=calendars_path,
    )


def _write_temp_registry_files(
    tmp_path: Path,
    *,
    source_rows: list[dict[str, str]] | None = None,
    trait_rows: list[dict[str, str]] | None = None,
    calendar_rows: list[dict[str, str]] | None = None,
) -> tuple[Path, Path, Path]:
    sources_path = tmp_path / "sources.csv"
    traits_path = tmp_path / "traits.csv"
    calendars_path = tmp_path / "calendars.csv"
    _write_csv(sources_path, SOURCE_FIELDS, source_rows if source_rows is not None else [_source()])
    _write_csv(traits_path, TRAIT_FIELDS, trait_rows if trait_rows is not None else [_trait()])
    _write_csv(
        calendars_path,
        CALENDAR_FIELDS,
        calendar_rows if calendar_rows is not None else [_calendar()],
    )
    return sources_path, traits_path, calendars_path


def test_curated_csv_files_load_successfully() -> None:
    registry = load_agronomy_registry()

    assert len(registry.sources) == 3
    assert len(registry.crop_traits) == 24
    assert len(registry.crop_calendars) == 5


@pytest.mark.parametrize("duplicate_kind", ["source", "trait", "calendar", "cross_file"])
def test_duplicate_ids_are_rejected(tmp_path: Path, duplicate_kind: str) -> None:
    if duplicate_kind == "source":
        rows = [_source(), {**_source(), "title": "Another source"}]
        with pytest.raises(ValueError, match="Duplicate source_id"):
            _load_temp_registry(tmp_path, source_rows=rows)
    elif duplicate_kind == "trait":
        rows = [_trait(), {**_trait(), "crop_id": "rice"}]
        with pytest.raises(ValueError, match="Duplicate record_id"):
            _load_temp_registry(tmp_path, trait_rows=rows)
    elif duplicate_kind == "calendar":
        rows = [_calendar(), {**_calendar(), "season": "Samba"}]
        with pytest.raises(ValueError, match="Duplicate record_id"):
            _load_temp_registry(tmp_path, calendar_rows=rows)
    else:
        calendar = {**_calendar(), "record_id": _trait()["record_id"]}
        with pytest.raises(ValueError, match="Duplicate record_id across claim files"):
            _load_temp_registry(tmp_path, calendar_rows=[calendar])


@pytest.mark.parametrize("source_id", ["", "UNKNOWN_SOURCE"])
def test_missing_or_unresolved_source_ids_are_rejected(
    tmp_path: Path,
    source_id: str,
) -> None:
    trait = {**_trait(), "source_id": source_id}

    with pytest.raises(ValueError, match="source_id"):
        _load_temp_registry(tmp_path, trait_rows=[trait])


def test_missing_source_locator_is_rejected(tmp_path: Path) -> None:
    trait = {**_trait(), "source_locator": ""}

    with pytest.raises(ValueError, match="source_locator"):
        _load_temp_registry(tmp_path, trait_rows=[trait])


@pytest.mark.parametrize(
    ("source_status", "claim_status"),
    [("VERIFIED", "VERIFIED"), ("UNVERIFIED", "UNVERIFIED")],
)
def test_claim_verification_status_may_match_source_status(
    tmp_path: Path,
    source_status: str,
    claim_status: str,
) -> None:
    source = {**_source(), "verification_status": source_status}
    trait = {**_trait(), "evidence_status": claim_status}
    calendar = {**_calendar(), "evidence_status": claim_status}

    registry = _load_temp_registry(
        tmp_path,
        source_rows=[source],
        trait_rows=[trait],
        calendar_rows=[calendar],
    )

    assert registry.sources[0].verification_status == source_status
    assert registry.crop_traits[0].evidence_status == claim_status
    assert registry.crop_calendars[0].evidence_status == claim_status


def test_verified_claim_cannot_reference_unverified_source(tmp_path: Path) -> None:
    source = {**_source(), "verification_status": "UNVERIFIED"}

    with pytest.raises(
        ValueError,
        match=r"VERIFIED claim 'TRAIT_A' references UNVERIFIED source 'SOURCE_A'",
    ):
        _load_temp_registry(tmp_path, source_rows=[source])


@pytest.mark.parametrize(
    ("column_count", "message"),
    [(len(TRAIT_FIELDS) - 1, "missing CSV columns"), (len(TRAIT_FIELDS) + 1, "extra CSV columns")],
)
def test_csv_rows_with_missing_or_extra_columns_are_rejected(
    tmp_path: Path,
    column_count: int,
    message: str,
) -> None:
    _, traits_path, _ = _write_temp_registry_files(tmp_path)
    with traits_path.open(encoding="utf-8", newline="") as file:
        contents = list(csv.reader(file))
    values = contents[1]
    if column_count < len(TRAIT_FIELDS):
        values = values[:column_count]
    else:
        values = [*values, "unexpected"]
    _write_csv_rows(traits_path, [contents[0], values])

    with pytest.raises(ValueError, match=rf"traits\.csv:2: {message}"):
        load_agronomy_registry(
            sources_path=tmp_path / "sources.csv",
            crop_traits_path=traits_path,
            crop_calendars_path=tmp_path / "calendars.csv",
        )


@pytest.mark.parametrize(
    ("header", "message"),
    [
        (TRAIT_FIELDS[:-1], "expected CSV columns"),
        ((*TRAIT_FIELDS[:-1], TRAIT_FIELDS[0]), "duplicate CSV headers"),
        (("unexpected", *TRAIT_FIELDS[1:]), "expected CSV columns"),
    ],
)
def test_mismatched_or_duplicate_csv_headers_are_rejected(
    tmp_path: Path,
    header: tuple[str, ...],
    message: str,
) -> None:
    _, traits_path, _ = _write_temp_registry_files(tmp_path)
    _write_csv_rows(traits_path, [list(header)])

    with pytest.raises(ValueError, match=rf"traits\.csv:1: {message}"):
        load_agronomy_registry(
            sources_path=tmp_path / "sources.csv",
            crop_traits_path=traits_path,
            crop_calendars_path=tmp_path / "calendars.csv",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("production_system_scope", "MIXED"),
        ("evidence_kind", "OBSERVED"),
        ("evidence_status", "CURRENT"),
        ("time_applicability", "RECENT"),
    ],
)
def test_invalid_controlled_values_are_rejected(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    trait = {**_trait(), field: value}

    with pytest.raises(ValueError, match=f"invalid {field}"):
        _load_temp_registry(tmp_path, trait_rows=[trait])


def test_unknown_calendar_dates_remain_blank_and_explicit(tmp_path: Path) -> None:
    registry = _load_temp_registry(tmp_path)
    calendar = registry.crop_calendars[0]

    assert calendar.window_status == "UNKNOWN"
    assert calendar.window_start is None
    assert calendar.window_end is None
    assert calendar.production_system_scope == "UNKNOWN"


@pytest.mark.parametrize(
    ("start", "end", "status"),
    [
        ("2020-05-01", "2020-04-30", "KNOWN"),
        ("2020-05-01", "", "KNOWN"),
        ("2020-05-01", "", "UNKNOWN"),
        ("2020-02-30", "2020-03-01", "KNOWN"),
    ],
)
def test_invalid_calendar_date_ranges_are_rejected(
    tmp_path: Path,
    start: str,
    end: str,
    status: str,
) -> None:
    calendar = {
        **_calendar(),
        "window_start": start,
        "window_end": end,
        "window_status": status,
    }

    with pytest.raises(ValueError, match="window_|window "):
        _load_temp_registry(tmp_path, calendar_rows=[calendar])


@pytest.mark.parametrize("value", ["-0.1", "100.1", "seventy-seven"])
def test_invalid_percentage_values_are_rejected(tmp_path: Path, value: str) -> None:
    trait = {**_trait(), "value": value}

    with pytest.raises(ValueError, match="percentage"):
        _load_temp_registry(tmp_path, trait_rows=[trait])


def test_historical_district_statistics_keep_scope_and_source_status() -> None:
    registry = load_agronomy_registry()
    cotton_rainfed = next(
        record
        for record in registry.crop_traits
        if record.record_id == "DAP_COTTON_RAINFED_SHARE"
    )

    assert cotton_rainfed.value == "77"
    assert cotton_rainfed.unit == "percent"
    assert cotton_rainfed.evidence_kind == "PUBLISHED_STATISTIC"
    assert cotton_rainfed.evidence_status == "VERIFIED"
    assert cotton_rainfed.time_applicability == "HISTORICAL"
    assert cotton_rainfed.geographic_scope == "Madurai district"
    assert cotton_rainfed.production_system_scope == "RAINFED"
    assert "not an individual farm" in cotton_rainfed.notes


def test_calendar_unknown_windows_are_not_inferred_from_season_names() -> None:
    registry = load_agronomy_registry()
    seasons = {record.season: record for record in registry.crop_calendars}

    assert {"Kuruvai", "Samba", "Navarai"} <= seasons.keys()
    assert all(seasons[name].window_status == "UNKNOWN" for name in ("Kuruvai", "Samba", "Navarai"))
    assert all(seasons[name].window_start is None for name in ("Kuruvai", "Samba", "Navarai"))
