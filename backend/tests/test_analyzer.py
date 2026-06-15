"""Tests for the deterministic abnormality analyzer."""

from __future__ import annotations

from healthadvocate.labs.analyzer import analyze, classify, is_abnormal
from healthadvocate.models import Direction, LabValue


def _v(value, low=135, high=145, available=True, name="Sodium", unit="mmol/L"):
    return LabValue(
        parameter=name, value=value, unit=unit,
        ref_low=low, ref_high=high, range_available=available,
    )


def test_classify_high():
    assert classify(148, 135, 145, True) is Direction.HIGH


def test_classify_low():
    assert classify(130, 135, 145, True) is Direction.LOW


def test_classify_in_range_returns_none():
    assert classify(140, 135, 145, True) is None


def test_boundaries_are_inclusive_normal():
    # exactly at the bounds is considered in range
    assert classify(135, 135, 145, True) is None
    assert classify(145, 135, 145, True) is None


def test_no_range_never_abnormal():
    assert classify(9999, None, None, False) is None
    assert is_abnormal(9999, None, None, False) is False


def test_one_sided_upper_bound():
    # e.g. parsed from "<1.3"
    assert classify(1.5, None, 1.3, True) is Direction.HIGH
    assert classify(1.0, None, 1.3, True) is None


def test_one_sided_lower_bound():
    # e.g. parsed from ">60"
    assert classify(50, 60, None, True) is Direction.LOW
    assert classify(70, 60, None, True) is None


def test_analyze_returns_only_abnormal_findings():
    values = [
        _v(148),                                   # Sodium high
        _v(4.2, low=3.5, high=5.1, name="Potassium", unit="mmol/L"),  # normal
        _v(12, low=None, high=None, available=False, name="Vitamin D", unit="ng/mL"),  # no range
        _v(60, low=70, high=100, name="Glucose", unit="mg/dL"),       # low
    ]
    findings = analyze(values)

    assert len(findings) == 2
    by_name = {f.parameter: f for f in findings}
    assert by_name["Sodium"].direction is Direction.HIGH
    assert by_name["Sodium"].value == 148
    assert by_name["Glucose"].direction is Direction.LOW


def test_analyze_empty():
    assert analyze([]) == []


def test_finding_preserves_range_and_unit():
    [finding] = analyze([_v(148)])
    assert finding.ref_low == 135 and finding.ref_high == 145
    assert finding.unit == "mmol/L"
