"""Tests for the deterministic lab-value parser."""

from __future__ import annotations

from datetime import date

from healthadvocate.ingestion.parser import detect_report_date, parse_lab_values

SAMPLE = """\
Comprehensive Metabolic Panel
Collected: 2026-05-01
Sodium 148 mmol/L 135-145
Potassium 4.2 mmol/L 3.5-5.1
Glucose, Fasting 90 mg/dL 70 - 99
Creatinine 0.9 mg/dL <1.3
eGFR 95 mL/min >60
Vitamin D 12 ng/mL
"""


def _by_name(values, name):
    return next(v for v in values if v.parameter == name)


def test_parses_numeric_range() -> None:
    values, _ = parse_lab_values(SAMPLE)
    sodium = _by_name(values, "Sodium")
    assert (sodium.value, sodium.unit) == (148.0, "mmol/L")
    assert (sodium.ref_low, sodium.ref_high) == (135.0, 145.0)
    assert sodium.range_available is True


def test_parses_en_dash_and_spaced_range() -> None:
    values, _ = parse_lab_values(SAMPLE)
    glucose = _by_name(values, "Glucose, Fasting")
    assert (glucose.ref_low, glucose.ref_high) == (70.0, 99.0)


def test_less_than_sets_upper_bound() -> None:
    values, _ = parse_lab_values(SAMPLE)
    creat = _by_name(values, "Creatinine")
    assert creat.ref_low is None
    assert creat.ref_high == 1.3
    assert creat.range_available is True


def test_greater_than_sets_lower_bound() -> None:
    values, _ = parse_lab_values(SAMPLE)
    egfr = _by_name(values, "eGFR")
    assert egfr.ref_low == 60.0
    assert egfr.ref_high is None


def test_no_range_marked_unavailable_and_warns() -> None:
    values, warnings = parse_lab_values(SAMPLE)
    vit_d = _by_name(values, "Vitamin D")
    assert vit_d.range_available is False
    assert vit_d.ref_low is None and vit_d.ref_high is None
    assert any("Vitamin D" in w for w in warnings)


def test_header_and_prose_lines_ignored() -> None:
    values, _ = parse_lab_values(SAMPLE)
    names = {v.parameter for v in values}
    assert "Comprehensive Metabolic Panel" not in names
    assert len(values) == 6


def test_detects_iso_collection_date() -> None:
    assert detect_report_date(SAMPLE) == date(2026, 5, 1)


def test_detects_us_date_format() -> None:
    text = "Patient report\nDate of Service: 05/01/2026\nSodium 140 mmol/L 135-145"
    assert detect_report_date(text) == date(2026, 5, 1)


def test_range_numbers_not_mistaken_for_date() -> None:
    text = "Sodium 140 mmol/L 135-145"
    assert detect_report_date(text) is None


def test_empty_text_yields_nothing() -> None:
    values, warnings = parse_lab_values("")
    assert values == [] and warnings == []
