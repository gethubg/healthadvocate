"""Pydantic schemas shared across the API and internal layers.

These types are the contract between layers (ingestion, storage, retrieval,
advisory) and the HTTP boundary. Keep them immutable-friendly: construct new
instances rather than mutating in place.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class Direction(str, Enum):
    """Which side of the reference range a value falls on."""

    HIGH = "high"
    LOW = "low"


class LabValue(BaseModel):
    """A single structured row extracted from a bloodwork report."""

    parameter: str = Field(..., description="Canonical parameter name, e.g. 'Sodium'.")
    value: float
    unit: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    range_available: bool = Field(
        ...,
        description="True only when a reference range was parsed from the report.",
    )


class Report(BaseModel):
    """Metadata for an uploaded bloodwork report."""

    report_id: str
    filename: str
    report_date: date = Field(..., description="User-entered blood-draw date (authoritative).")
    uploaded_at: datetime = Field(..., description="Server receipt time; tiebreaker only.")


class UploadResponse(BaseModel):
    """Response for POST /reports."""

    report_id: str
    filename: str
    report_date: date
    uploaded_at: datetime
    parsed_parameters: list[LabValue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReportListResponse(BaseModel):
    """Response for GET /reports."""

    reports: list[Report] = Field(default_factory=list)


class AbnormalFinding(BaseModel):
    """A parameter whose value falls outside its report-printed reference range."""

    parameter: str
    value: float
    unit: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    direction: Direction


class Source(BaseModel):
    """A cited web source backing a piece of advice."""

    title: str
    url: str


class FoodAdvice(BaseModel):
    """Foods to avoid for one abnormal parameter, with sources."""

    parameter: str
    foods_to_avoid: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


class AskRequest(BaseModel):
    """Request body for POST /ask."""

    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    """Response for POST /ask."""

    answer: str
    report_id: str | None = None
    report_date: date | None = None
    findings: list[AbnormalFinding] = Field(default_factory=list)
    advice: list[FoodAdvice] = Field(default_factory=list)


class TrendPoint(BaseModel):
    """A single point in a parameter's time series."""

    report_date: date
    value: float
    ref_low: float | None = None
    ref_high: float | None = None
    abnormal: bool


class TrendSeries(BaseModel):
    """Response for GET /trends."""

    parameter: str
    unit: str | None = None
    points: list[TrendPoint] = Field(default_factory=list)
