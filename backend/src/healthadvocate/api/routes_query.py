"""Question-answering route (Ask tab)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from healthadvocate.advisor.food_advisor import FoodAdvisor
from healthadvocate.api.deps import get_food_advisor, get_lab_store, get_query_engine
from healthadvocate.labs.analyzer import analyze
from healthadvocate.models import AskRequest, AskResponse
from healthadvocate.retrieval.query_engine import BloodworkQueryEngine, NoReportsError
from healthadvocate.storage.lab_store import LabStore

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    engine: BloodworkQueryEngine = Depends(get_query_engine),
    lab_store: LabStore = Depends(get_lab_store),
    advisor: FoodAdvisor = Depends(get_food_advisor),
) -> AskResponse:
    try:
        result = engine.ask(body.question)
    except NoReportsError as exc:
        raise HTTPException(404, str(exc)) from exc

    # Deterministic abnormality detection over the latest report's values,
    # then conditional web advice only for what is abnormal.
    values = lab_store.get_values_for_report(result.report.report_id)
    findings = analyze(values)
    advice = advisor.advise_all(findings)

    return AskResponse(
        answer=result.answer,
        report_id=result.report.report_id,
        report_date=result.report.report_date,
        findings=findings,
        advice=advice,
    )
