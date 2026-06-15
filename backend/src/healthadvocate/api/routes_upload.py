"""Upload and report-listing routes."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from healthadvocate.api.deps import (
    get_indexer,
    get_lab_extractor,
    get_lab_store,
    get_pdf_store,
)
from healthadvocate.config import get_settings
from healthadvocate.ingestion.extraction import LabExtractor
from healthadvocate.ingestion.indexer import Indexer
from healthadvocate.ingestion.parser import extract_text
from healthadvocate.ingestion.pdf_store import PdfStore
from healthadvocate.models import Report, ReportListResponse, UploadResponse
from healthadvocate.storage.lab_store import LabStore

router = APIRouter(tags=["reports"])
logger = logging.getLogger(__name__)


def _parse_report_date(raw: str) -> date:
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(400, f"Invalid report_date '{raw}'; expected YYYY-MM-DD.") from exc
    if parsed > datetime.now(UTC).date():
        raise HTTPException(400, "report_date cannot be in the future.")
    return parsed


@router.post("/reports", response_model=UploadResponse, status_code=201)
async def upload_report(
    file: UploadFile = File(...),
    report_date: str = Form(...),
    pdf_store: PdfStore = Depends(get_pdf_store),
    indexer: Indexer = Depends(get_indexer),
    extractor: LabExtractor = Depends(get_lab_extractor),
) -> UploadResponse:
    parsed_date = _parse_report_date(report_date)

    filename = file.filename or "report.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    content = await file.read()
    max_bytes = get_settings().max_upload_bytes
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds the {get_settings().max_upload_mb} MB limit.")

    try:
        text = extract_text(content)
    except Exception as exc:
        raise HTTPException(400, f"Could not read PDF: {exc}") from exc

    values, warnings = extractor.extract(text)

    stored = pdf_store.save(filename, content)
    uploaded_at = datetime.now(UTC)
    report = Report(
        report_id=stored.report_id,
        filename=stored.filename,
        report_date=parsed_date,
        uploaded_at=uploaded_at,
    )
    indexer.index_report(report, text, values)

    return UploadResponse(
        report_id=report.report_id,
        filename=report.filename,
        report_date=report.report_date,
        uploaded_at=report.uploaded_at,
        parsed_parameters=values,
        warnings=warnings,
    )


@router.get("/reports", response_model=ReportListResponse)
def list_reports(lab_store: LabStore = Depends(get_lab_store)) -> ReportListResponse:
    return ReportListResponse(reports=lab_store.list_reports())


@router.delete("/reports/{report_id}", status_code=204)
def delete_report(
    report_id: str,
    lab_store: LabStore = Depends(get_lab_store),
    pdf_store: PdfStore = Depends(get_pdf_store),
    indexer: Indexer = Depends(get_indexer),
) -> Response:
    """Remove a report from all three stores (SQLite, PDF file, Pinecone)."""
    known = {r.report_id for r in lab_store.list_reports()}
    if report_id not in known:
        raise HTTPException(404, f"No report with id '{report_id}'.")

    # SQLite + the PDF file are authoritative for the UI; delete them first.
    lab_store.delete_report(report_id)
    pdf_store.delete(report_id)

    # Vector cleanup is networked and best-effort — a failure here must not leave
    # the report half-deleted from the user's perspective.
    try:
        indexer.delete_vectors(report_id)
    except Exception:
        logger.warning("Failed to delete vectors for %s; rows/file removed", report_id)

    return Response(status_code=204)
