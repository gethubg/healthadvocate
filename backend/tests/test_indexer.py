"""Tests for the Indexer — vector path mocked, lab_store path real."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from healthadvocate.config import get_settings
from healthadvocate.ingestion.indexer import Indexer
from healthadvocate.models import LabValue, Report
from healthadvocate.storage.lab_store import LabStore


@pytest.fixture
def report() -> Report:
    return Report(
        report_id="rpt_1",
        filename="a.pdf",
        report_date=date(2026, 5, 1),
        uploaded_at=datetime(2026, 6, 15, 10, 0, 0),
    )


@pytest.fixture
def store(tmp_path) -> LabStore:
    return LabStore(tmp_path / "test.db")


def test_index_writes_structured_rows_and_calls_vector_writer(store, report) -> None:
    # Arrange — capture what the vector writer receives
    captured: dict = {}

    def fake_writer(rpt: Report, text: str) -> None:
        captured["report"] = rpt
        captured["text"] = text

    values = [
        LabValue(parameter="Sodium", value=148, unit="mmol/L",
                 ref_low=135, ref_high=145, range_available=True),
    ]
    indexer = Indexer(store, get_settings(), vector_writer=fake_writer)

    # Act
    indexer.index_report(report, "Sodium 148 mmol/L 135-145", values)

    # Assert — lab_store persisted
    assert store.get_latest_report().report_id == "rpt_1"
    assert len(store.get_values_for_report("rpt_1")) == 1
    # Assert — vector writer received report + text
    assert captured["report"].report_id == "rpt_1"
    assert "Sodium" in captured["text"]


def test_structured_rows_persist_even_if_vector_writer_fails(store, report) -> None:
    # Arrange — vector step raises (e.g. network down)
    def boom(rpt: Report, text: str) -> None:
        raise RuntimeError("pinecone unreachable")

    values = [
        LabValue(parameter="Sodium", value=148, unit="mmol/L",
                 ref_low=135, ref_high=145, range_available=True),
    ]
    indexer = Indexer(store, get_settings(), vector_writer=boom)

    # Act / Assert — error propagates, but rows were written first
    with pytest.raises(RuntimeError):
        indexer.index_report(report, "text", values)
    assert store.get_values_for_report("rpt_1")  # structured data survived
