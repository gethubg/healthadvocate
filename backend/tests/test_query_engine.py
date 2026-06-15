"""Tests for the latest-report query orchestration (responder mocked)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from healthadvocate.models import LabValue, Report
from healthadvocate.retrieval.query_engine import BloodworkQueryEngine, NoReportsError
from healthadvocate.storage.lab_store import LabStore


class FakeResponder:
    """Records the report_id it was scoped to and echoes it back."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def answer(self, question: str, report_id: str) -> str:
        self.calls.append((question, report_id))
        return f"answer for {report_id}"


@pytest.fixture
def store(tmp_path) -> LabStore:
    return LabStore(tmp_path / "test.db")


def _report(rid: str, rdate: str, uploaded: str = "2026-06-15T10:00:00") -> Report:
    return Report(
        report_id=rid, filename=f"{rid}.pdf",
        report_date=date.fromisoformat(rdate), uploaded_at=datetime.fromisoformat(uploaded),
    )


def _sodium(v: float) -> LabValue:
    return LabValue(parameter="Sodium", value=v, unit="mmol/L",
                    ref_low=135, ref_high=145, range_available=True)


def test_ask_scopes_to_latest_report_by_report_date(store) -> None:
    # Arrange — older report uploaded later; report_date must win
    store.save_report(_report("new", "2026-05-01", "2026-06-01T09:00:00"), [_sodium(148)])
    store.save_report(_report("old", "2026-01-10", "2026-06-15T09:00:00"), [_sodium(140)])
    responder = FakeResponder()
    engine = BloodworkQueryEngine(store, responder)

    # Act
    result = engine.ask("Is my sodium okay?")

    # Assert — responder scoped to the latest report only
    assert result.report.report_id == "new"
    assert responder.calls == [("Is my sodium okay?", "new")]
    assert result.answer == "answer for new"


def test_ask_without_reports_raises(store) -> None:
    engine = BloodworkQueryEngine(store, FakeResponder())
    with pytest.raises(NoReportsError):
        engine.ask("anything")
