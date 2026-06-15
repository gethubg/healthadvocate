"""Tests for the SQLite lab_store."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from healthadvocate.models import LabValue, Report
from healthadvocate.storage.lab_store import LabStore


@pytest.fixture
def store(tmp_path) -> LabStore:
    return LabStore(tmp_path / "test.db")


def _report(report_id: str, report_date: str, uploaded_at: str = "2026-06-15T10:00:00") -> Report:
    return Report(
        report_id=report_id,
        filename=f"{report_id}.pdf",
        report_date=date.fromisoformat(report_date),
        uploaded_at=datetime.fromisoformat(uploaded_at),
    )


def _sodium(value: float, low: float = 135, high: float = 145) -> LabValue:
    return LabValue(
        parameter="Sodium", value=value, unit="mmol/L",
        ref_low=low, ref_high=high, range_available=True,
    )


def test_save_and_list_reports_sorted_by_report_date(store: LabStore) -> None:
    # Arrange
    store.save_report(_report("r1", "2026-01-10"), [_sodium(140)])
    store.save_report(_report("r2", "2026-05-01"), [_sodium(148)])

    # Act
    reports = store.list_reports()

    # Assert — most recent report_date first
    assert [r.report_id for r in reports] == ["r2", "r1"]


def test_latest_report_uses_report_date_not_upload_time(store: LabStore) -> None:
    # Arrange — r_old uploaded LATER but has an EARLIER report_date
    store.save_report(_report("r_new", "2026-05-01", "2026-06-01T09:00:00"), [_sodium(148)])
    store.save_report(_report("r_old", "2026-01-10", "2026-06-15T09:00:00"), [_sodium(140)])

    # Act
    latest = store.get_latest_report()

    # Assert — recency is by report_date, so r_new wins despite later upload
    assert latest is not None
    assert latest.report_id == "r_new"


def test_uploaded_at_breaks_report_date_ties(store: LabStore) -> None:
    # Arrange — same report_date, different upload times
    store.save_report(_report("early", "2026-05-01", "2026-06-01T09:00:00"), [_sodium(140)])
    store.save_report(_report("late", "2026-05-01", "2026-06-10T09:00:00"), [_sodium(148)])

    # Act / Assert
    latest = store.get_latest_report()
    assert latest is not None
    assert latest.report_id == "late"


def test_get_latest_report_none_when_empty(store: LabStore) -> None:
    assert store.get_latest_report() is None


def test_get_values_for_report(store: LabStore) -> None:
    # Arrange
    store.save_report(_report("r1", "2026-05-01"), [_sodium(148), _sodium(140)])

    # Act
    values = store.get_values_for_report("r1")

    # Assert
    assert len(values) == 2
    assert all(v.parameter == "Sodium" for v in values)


def test_trend_is_case_insensitive_and_ordered(store: LabStore) -> None:
    # Arrange — unordered insertion, mixed-case query
    store.save_report(_report("r2", "2026-05-01"), [_sodium(148)])
    store.save_report(_report("r1", "2026-01-10"), [_sodium(140)])

    # Act
    series = store.get_trend("SODIUM")

    # Assert — ascending by report_date
    assert series is not None
    assert [p.report_date.isoformat() for p in series.points] == ["2026-01-10", "2026-05-01"]
    assert series.unit == "mmol/L"


def test_trend_flags_abnormal_points(store: LabStore) -> None:
    # Arrange
    store.save_report(_report("r1", "2026-01-10"), [_sodium(140)])  # in range
    store.save_report(_report("r2", "2026-05-01"), [_sodium(148)])  # high

    # Act
    series = store.get_trend("sodium")

    # Assert
    assert series is not None
    assert [p.abnormal for p in series.points] == [False, True]


def test_trend_respects_date_range(store: LabStore) -> None:
    # Arrange
    store.save_report(_report("r1", "2026-01-10"), [_sodium(140)])
    store.save_report(_report("r2", "2026-05-01"), [_sodium(148)])
    store.save_report(_report("r3", "2026-09-01"), [_sodium(150)])

    # Act
    series = store.get_trend("sodium", date_from=date(2026, 2, 1), date_to=date(2026, 6, 1))

    # Assert — only r2 falls in the window
    assert series is not None
    assert [p.report_date.isoformat() for p in series.points] == ["2026-05-01"]


def test_trend_missing_parameter_returns_none(store: LabStore) -> None:
    store.save_report(_report("r1", "2026-05-01"), [_sodium(140)])
    assert store.get_trend("potassium") is None


def test_value_without_range_never_abnormal(store: LabStore) -> None:
    # Arrange — no reference range available
    no_range = LabValue(
        parameter="VitaminD", value=12.0, unit="ng/mL",
        ref_low=None, ref_high=None, range_available=False,
    )
    store.save_report(_report("r1", "2026-05-01"), [no_range])

    # Act
    series = store.get_trend("vitamind")

    # Assert — honors "never invent a range"
    assert series is not None
    assert series.points[0].abnormal is False


def test_save_report_is_idempotent(store: LabStore) -> None:
    # Arrange — save same report_id twice
    store.save_report(_report("r1", "2026-05-01"), [_sodium(148)])
    store.save_report(_report("r1", "2026-05-01"), [_sodium(140), _sodium(142)])

    # Act
    values = store.get_values_for_report("r1")

    # Assert — old rows replaced, not duplicated
    assert len(values) == 2
    assert len(store.list_reports()) == 1
