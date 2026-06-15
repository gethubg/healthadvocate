"""Integration tests for the HTTP API with network-bound deps overridden."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from healthadvocate.advisor.ddg_search import SearchResult
from healthadvocate.advisor.food_advisor import FoodAdvisor
from healthadvocate.api import deps, routes_upload
from healthadvocate.api.main import create_app
from healthadvocate.config import get_settings
from healthadvocate.ingestion.extraction import RegexLabExtractor
from healthadvocate.ingestion.indexer import Indexer
from healthadvocate.ingestion.pdf_store import PdfStore
from healthadvocate.models import LabValue, Report
from healthadvocate.retrieval.query_engine import BloodworkQueryEngine
from healthadvocate.storage.lab_store import LabStore

SAMPLE_TEXT = """\
Collected: 2026-05-01
Sodium 148 mmol/L 135-145
Potassium 4.2 mmol/L 3.5-5.1
"""


class FakeResponder:
    def answer(self, question: str, report_id: str) -> str:
        return f"Grounded answer for {report_id}"


class FakeSearch:
    def search(self, query: str, max_results: int = 5):
        return [SearchResult("Low sodium diet", "https://ex.com/sodium", "Avoid salty snacks")]


class FakeSynth:
    def synthesize(self, parameter, direction, results):
        return ["Salty snacks", "Canned soup"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = LabStore(tmp_path / "test.db")
    pdf_store = PdfStore(tmp_path / "pdfs")
    settings = get_settings()

    # Indexer with no-op vector writer/deleter (no Pinecone/OpenAI).
    indexer = Indexer(
        store,
        settings,
        vector_writer=lambda report, text: None,
        vector_deleter=lambda report_id: None,
    )

    app = create_app()
    app.dependency_overrides[deps.get_lab_store] = lambda: store
    app.dependency_overrides[deps.get_pdf_store] = lambda: pdf_store
    app.dependency_overrides[deps.get_indexer] = lambda: indexer
    app.dependency_overrides[deps.get_query_engine] = lambda: BloodworkQueryEngine(
        store, FakeResponder()
    )
    app.dependency_overrides[deps.get_food_advisor] = lambda: FoodAdvisor(
        FakeSearch(), FakeSynth()
    )
    # Use the deterministic regex extractor so uploads don't call OpenAI.
    app.dependency_overrides[deps.get_lab_extractor] = lambda: RegexLabExtractor()

    # Bypass real PDF byte parsing — parser is unit-tested separately.
    monkeypatch.setattr(routes_upload, "extract_text", lambda content: SAMPLE_TEXT)

    return TestClient(app), store


def _seed(store: LabStore) -> None:
    store.save_report(
        Report(
            report_id="rpt_seed", filename="seed.pdf",
            report_date=date(2026, 5, 1), uploaded_at=datetime(2026, 6, 15, 10, 0, 0),
        ),
        [
            LabValue(parameter="Sodium", value=148, unit="mmol/L",
                     ref_low=135, ref_high=145, range_available=True),
            LabValue(parameter="Potassium", value=4.2, unit="mmol/L",
                     ref_low=3.5, ref_high=5.1, range_available=True),
        ],
    )


def test_upload_then_list(client) -> None:
    api, _ = client

    resp = api.post(
        "/reports",
        files={"file": ("labs.pdf", b"%PDF-1.7 fake", "application/pdf")},
        data={"report_date": "2026-05-01"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["report_date"] == "2026-05-01"
    params = {p["parameter"] for p in body["parsed_parameters"]}
    assert params == {"Sodium", "Potassium"}

    listing = api.get("/reports").json()
    assert len(listing["reports"]) == 1


def test_upload_rejects_future_date(client) -> None:
    api, _ = client
    resp = api.post(
        "/reports",
        files={"file": ("labs.pdf", b"x", "application/pdf")},
        data={"report_date": "2099-01-01"},
    )
    assert resp.status_code == 400


def test_upload_rejects_non_pdf(client) -> None:
    api, _ = client
    resp = api.post(
        "/reports",
        files={"file": ("labs.txt", b"x", "text/plain")},
        data={"report_date": "2026-05-01"},
    )
    assert resp.status_code == 400


def test_ask_returns_answer_findings_and_advice(client) -> None:
    api, store = client
    _seed(store)

    resp = api.post("/ask", json={"question": "Is my sodium okay?"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["report_id"] == "rpt_seed"
    assert "Grounded answer" in body["answer"]
    # Only Sodium (148 > 145) is abnormal; Potassium is in range.
    assert [f["parameter"] for f in body["findings"]] == ["Sodium"]
    assert body["findings"][0]["direction"] == "high"
    assert body["advice"][0]["foods_to_avoid"] == ["Salty snacks", "Canned soup"]


def test_ask_without_reports_returns_404(client) -> None:
    api, _ = client
    resp = api.post("/ask", json={"question": "anything"})
    assert resp.status_code == 404


def test_trends_returns_series(client) -> None:
    api, store = client
    _seed(store)

    resp = api.get("/trends", params={"parameter": "sodium"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["parameter"] == "Sodium"
    assert body["points"][0]["abnormal"] is True


def test_trends_unknown_parameter_404(client) -> None:
    api, store = client
    _seed(store)
    resp = api.get("/trends", params={"parameter": "cholesterol"})
    assert resp.status_code == 404


def test_trends_bad_date_range_400(client) -> None:
    api, store = client
    _seed(store)
    resp = api.get(
        "/trends",
        params={"parameter": "sodium", "from": "2026-06-01", "to": "2026-01-01"},
    )
    assert resp.status_code == 400


def test_delete_report_removes_it(client) -> None:
    api, store = client
    _seed(store)
    assert len(api.get("/reports").json()["reports"]) == 1

    resp = api.delete("/reports/rpt_seed")
    assert resp.status_code == 204
    assert api.get("/reports").json()["reports"] == []


def test_delete_unknown_report_404(client) -> None:
    api, _ = client
    resp = api.delete("/reports/rpt_nope")
    assert resp.status_code == 404
