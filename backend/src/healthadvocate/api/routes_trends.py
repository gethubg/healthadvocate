"""Trend time-series route (Trends tab)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from healthadvocate.api.deps import get_lab_store
from healthadvocate.models import TrendSeries
from healthadvocate.storage.lab_store import LabStore

router = APIRouter(tags=["trends"])


@router.get("/trends", response_model=TrendSeries)
def trends(
    parameter: str = Query(..., min_length=1),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    lab_store: LabStore = Depends(get_lab_store),
) -> TrendSeries:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(400, "'from' must not be after 'to'.")

    series = lab_store.get_trend(parameter, date_from=date_from, date_to=date_to)
    if series is None:
        raise HTTPException(404, f"No data for parameter '{parameter}'.")
    return series
