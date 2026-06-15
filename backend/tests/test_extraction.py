"""Tests for the hybrid regex+LLM lab extractor."""

from __future__ import annotations

from types import SimpleNamespace

from healthadvocate.config import get_settings
from healthadvocate.ingestion.extraction import (
    HybridLabExtractor,
    LlmLabExtractor,
    RegexLabExtractor,
)
from healthadvocate.models import LabValue

REGEX_FRIENDLY = "Sodium 148 mmol/L 135-145\n"
REGEX_HOSTILE = "| Creatinine | 1.5 | mg/dL | 0.6 - 1.3 |"  # pipe table the regex won't read


class FakeLlm:
    """Returns preset values, or raises if configured to simulate an outage."""

    def __init__(self, values: list[LabValue], raises: bool = False) -> None:
        self._values = values
        self._raises = raises
        self.called = False

    def extract(self, text: str):
        self.called = True
        if self._raises:
            raise RuntimeError("openai unavailable")
        return self._values, []


def _creatinine() -> LabValue:
    return LabValue(parameter="Creatinine", value=1.5, unit="mg/dL",
                    ref_low=0.6, ref_high=1.3, range_available=True)


def test_hybrid_prefers_llm_and_reads_layouts_regex_cannot():
    llm = FakeLlm([_creatinine()])
    hybrid = HybridLabExtractor(RegexLabExtractor(), llm)

    values, _ = hybrid.extract(REGEX_HOSTILE)  # pipe table regex can't read

    assert llm.called is True
    assert values[0].parameter == "Creatinine"


def test_hybrid_augments_llm_with_regex_only_params():
    # LLM returns Creatinine; regex independently reads Sodium from the text.
    llm = FakeLlm([_creatinine()])
    hybrid = HybridLabExtractor(RegexLabExtractor(), llm)

    text = REGEX_FRIENDLY  # "Sodium 148 mmol/L 135-145"
    values, _ = hybrid.extract(text)

    names = {v.parameter for v in values}
    assert names == {"Creatinine", "Sodium"}


def test_hybrid_falls_back_to_regex_when_llm_unavailable():
    llm = FakeLlm([], raises=True)
    hybrid = HybridLabExtractor(RegexLabExtractor(), llm)

    values, _ = hybrid.extract(REGEX_FRIENDLY)

    assert llm.called is True
    assert [v.parameter for v in values] == ["Sodium"]  # deterministic fallback


def test_hybrid_falls_back_when_llm_returns_nothing():
    llm = FakeLlm([])
    hybrid = HybridLabExtractor(RegexLabExtractor(), llm)

    values, _ = hybrid.extract(REGEX_FRIENDLY)

    assert [v.parameter for v in values] == ["Sodium"]


def test_llm_to_values_parses_rows_and_one_sided_ranges():
    rows = [
        {"parameter": "Creatinine", "value": 1.5, "unit": "mg/dL", "ref_low": 0.6, "ref_high": 1.3},
        {"parameter": "eGFR", "value": 95, "unit": "mL/min", "ref_low": 60, "ref_high": None},
        {"parameter": "Vitamin D", "value": 12, "unit": "ng/mL", "ref_low": None, "ref_high": None},
    ]
    values, warnings = LlmLabExtractor._to_values(rows)

    by_name = {v.parameter: v for v in values}
    assert by_name["Creatinine"].range_available is True
    assert by_name["eGFR"].ref_low == 60 and by_name["eGFR"].ref_high is None
    assert by_name["Vitamin D"].range_available is False
    assert any("Vitamin D" in w for w in warnings)


def test_llm_to_values_skips_malformed_rows():
    rows = [
        {"parameter": "Sodium", "value": "not a number"},
        {"value": 5},  # missing parameter
        {"parameter": "Potassium", "value": 4.2, "ref_low": 3.5, "ref_high": 5.1},
    ]
    values, _ = LlmLabExtractor._to_values(rows)

    assert [v.parameter for v in values] == ["Potassium"]


def test_llm_extractor_builds_message_without_format_crash(monkeypatch):
    """Regression: the prompt contains literal JSON braces. Building the request
    via str.format() crashed with KeyError and silently degraded every upload."""
    import openai

    captured: dict = {}
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"values": [{"parameter": "Sodium", "value": 140, '
                    '"unit": "mmol/L", "ref_low": 135, "ref_high": 145}]}'
                )
            )
        ]
    )

    class FakeCompletions:
        def create(self, **kwargs):
            captured["content"] = kwargs["messages"][0]["content"]
            return response

    class FakeClient:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(openai, "OpenAI", FakeClient)

    values, _ = LlmLabExtractor(get_settings()).extract("Sodium 140 mmol/L 135-145")

    assert values[0].parameter == "Sodium"
    # The literal JSON template and the report text must both survive into the prompt.
    assert '{"values"' in captured["content"]
    assert "Sodium 140 mmol/L 135-145" in captured["content"]
