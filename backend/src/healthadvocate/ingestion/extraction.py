"""Lab-value extraction strategies.

The deterministic regex parser handles clean single-line layouts cheaply. Real
lab PDFs often use multi-column tables or split rows the regex can't read, so a
``HybridLabExtractor`` falls back to an LLM extractor when the regex finds
nothing usable. Detection of *abnormality* remains deterministic — the LLM only
reads the table into structured rows; it never decides what is "abnormal".

All extractors return ``(values, warnings)``. The LLM path is behind the
``LabExtractor`` protocol so the upload flow is testable without network.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

from healthadvocate.config import Settings
from healthadvocate.ingestion.parser import parse_lab_values
from healthadvocate.models import LabValue

logger = logging.getLogger(__name__)


class LabExtractor(Protocol):
    def extract(self, text: str) -> tuple[list[LabValue], list[str]]: ...


class RegexLabExtractor:
    """Deterministic line/regex extraction (see parser.parse_lab_values)."""

    def extract(self, text: str) -> tuple[list[LabValue], list[str]]:
        return parse_lab_values(text)


class HybridLabExtractor:
    """LLM-primary extraction with regex as a safety net.

    The LLM reads arbitrary table layouts far more reliably than regex, so it is
    the primary path. Regex is used to (a) fully fall back when the LLM is
    unavailable or returns nothing (no key, network error), and (b) augment the
    LLM result with any parameters it missed. This avoids the failure mode where
    regex finds *some* rows and silently drops the ones it can't read.
    """

    def __init__(self, regex: LabExtractor, llm: LabExtractor) -> None:
        self._regex = regex
        self._llm = llm

    def extract(self, text: str) -> tuple[list[LabValue], list[str]]:
        try:
            llm_values, llm_warnings = self._llm.extract(text)
        except Exception:
            # Don't hide it — a swallowed failure here silently degrades every
            # upload to the noisy regex path. Log loudly, then fall back.
            logger.exception("LLM lab extraction failed; falling back to regex")
            llm_values, llm_warnings = [], []

        if not llm_values:
            # LLM unavailable or read nothing — fall back to deterministic regex.
            return self._regex.extract(text)

        # LLM succeeded; add any parameters regex caught that the LLM missed.
        regex_values, _ = self._regex.extract(text)
        seen = {v.parameter.strip().lower() for v in llm_values}
        extras = [v for v in regex_values if v.parameter.strip().lower() not in seen]
        return llm_values + extras, llm_warnings


class LlmLabExtractor:
    """Reads lab rows from arbitrary report text via OpenAI structured output."""

    # NOTE: contains literal JSON braces — build the message by concatenation, never
    # str.format()/f-string, or the braces are parsed as replacement fields.
    _INSTRUCTIONS = (
        "Extract every laboratory test result from the report text below. "
        "Return ONLY JSON of the form "
        '{"values": [{"parameter": str, "value": number, "unit": str|null, '
        '"ref_low": number|null, "ref_high": number|null}]}. '
        "Use the reference range printed in the report; set ref_low/ref_high to "
        "null if a bound is absent. For a one-sided range like '<1.3', set "
        "ref_high=1.3 and ref_low=null; for '>60', set ref_low=60. Do NOT invent "
        "ranges. Skip rows without a numeric result.\n\nReport text:\n"
    )

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract(self, text: str) -> tuple[list[LabValue], list[str]]:
        from openai import OpenAI

        client = OpenAI(api_key=self._settings.openai_api_key)
        completion = client.chat.completions.create(
            model=self._settings.openai_llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": self._INSTRUCTIONS + text}],
        )
        payload = json.loads(completion.choices[0].message.content or "{}")
        return self._to_values(payload.get("values", []))

    @staticmethod
    def _to_values(rows: list[dict]) -> tuple[list[LabValue], list[str]]:
        values: list[LabValue] = []
        warnings: list[str] = []
        for row in rows:
            try:
                value = float(row["value"])
            except (KeyError, TypeError, ValueError):
                continue
            ref_low = _as_float(row.get("ref_low"))
            ref_high = _as_float(row.get("ref_high"))
            range_available = ref_low is not None or ref_high is not None
            parameter = str(row.get("parameter", "")).strip()
            if not parameter:
                continue
            if not range_available:
                warnings.append(f"Parameter '{parameter}' has no parseable reference range.")
            values.append(
                LabValue(
                    parameter=parameter,
                    value=value,
                    unit=(str(row["unit"]).strip() if row.get("unit") else None),
                    ref_low=ref_low,
                    ref_high=ref_high,
                    range_available=range_available,
                )
            )
        return values, warnings


def _as_float(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def build_default_extractor(settings: Settings) -> HybridLabExtractor:
    return HybridLabExtractor(RegexLabExtractor(), LlmLabExtractor(settings))
