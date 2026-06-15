"""Tests for the PDF filesystem store."""

from __future__ import annotations

import pytest

from healthadvocate.ingestion.pdf_store import PdfStore


@pytest.fixture
def store(tmp_path) -> PdfStore:
    return PdfStore(tmp_path / "pdfs")


def test_save_writes_file_and_returns_metadata(store: PdfStore) -> None:
    stored = store.save("labcorp.pdf", b"%PDF-1.7 fake")

    assert stored.report_id.startswith("rpt_")
    assert stored.filename == "labcorp.pdf"
    assert stored.path.exists()
    assert stored.path.read_bytes() == b"%PDF-1.7 fake"


def test_read_round_trips(store: PdfStore) -> None:
    stored = store.save("a.pdf", b"content")
    assert store.read(stored.report_id) == b"content"


def test_report_ids_are_unique(store: PdfStore) -> None:
    a = store.save("a.pdf", b"x")
    b = store.save("b.pdf", b"y")
    assert a.report_id != b.report_id


def test_read_missing_raises(store: PdfStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.read("rpt_missing")


def test_delete_removes_file(store: PdfStore) -> None:
    stored = store.save("a.pdf", b"x")
    store.delete(stored.report_id)
    assert not stored.path.exists()
