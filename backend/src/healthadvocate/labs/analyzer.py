"""Deterministic abnormality detection.

The single source of truth for "is this value abnormal?" — used by both the
/ask flow (to produce AbnormalFinding objects that trigger food advice) and the
lab_store (to flag trend points). No LLM is involved: this is a pure, auditable
comparison against the report-printed reference range.

Rule (honoring "never invent a range", see SAFETY_DISCLAIMER.md):
  * range_available is False        -> never abnormal (no basis to judge)
  * value < ref_low (if present)    -> LOW
  * value > ref_high (if present)   -> HIGH
  * otherwise                       -> in range
"""

from __future__ import annotations

from healthadvocate.models import AbnormalFinding, Direction, LabValue


def classify(
    value: float,
    ref_low: float | None,
    ref_high: float | None,
    range_available: bool,
) -> Direction | None:
    """Return HIGH/LOW if out of range, else None. None also when no range."""
    if not range_available:
        return None
    if ref_low is not None and value < ref_low:
        return Direction.LOW
    if ref_high is not None and value > ref_high:
        return Direction.HIGH
    return None


def is_abnormal(
    value: float,
    ref_low: float | None,
    ref_high: float | None,
    range_available: bool,
) -> bool:
    """Boolean convenience wrapper over :func:`classify`."""
    return classify(value, ref_low, ref_high, range_available) is not None


def analyze(values: list[LabValue]) -> list[AbnormalFinding]:
    """Produce AbnormalFinding objects for every out-of-range value."""
    findings: list[AbnormalFinding] = []
    for v in values:
        direction = classify(v.value, v.ref_low, v.ref_high, v.range_available)
        if direction is None:
            continue
        findings.append(
            AbnormalFinding(
                parameter=v.parameter,
                value=v.value,
                unit=v.unit,
                ref_low=v.ref_low,
                ref_high=v.ref_high,
                direction=direction,
            )
        )
    return findings
