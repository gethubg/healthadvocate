"""Parse bloodwork PDFs into raw text + structured lab values.

Design notes
------------
Detection is **deterministic** (regex/line-based), not LLM-driven, so it is
testable and auditable. Reference ranges come *only* from the report — rows
without a parseable range are kept with ``range_available=False`` and a warning;
we never invent a range (see SAFETY_DISCLAIMER.md).

Three line grammars are attempted in order:
  A. numeric range        ``Sodium 148 mmol/L 135-145``
  B. inequality range     ``Creatinine 0.9 mg/dL <1.3``
  C. value, no range      ``Vitamin D 12 ng/mL``  -> range_available=False
Lines matching none of these (headers, prose) are ignored.
"""

from __future__ import annotations

import re
from datetime import date

from healthadvocate.models import LabValue

# Shared sub-patterns
_PARAM = r"(?P<param>[A-Za-z][A-Za-z ,.()/%-]+?)"
_VALUE = r"(?P<value>\d+(?:\.\d+)?)"
_UNIT = r"(?:\s+(?P<unit>[A-Za-zµμ%][A-Za-zµμ%/0-9.^*]*))?"
_NUM = r"\d+(?:\.\d+)?"

_RE_NUMERIC = re.compile(
    rf"^{_PARAM}\s+{_VALUE}{_UNIT}\s+(?P<low>{_NUM})\s*[-–]\s*(?P<high>{_NUM})\s*$"
)
_RE_INEQUALITY = re.compile(
    rf"^{_PARAM}\s+{_VALUE}{_UNIT}\s+(?P<ineq>[<>])\s*(?P<bound>{_NUM})\s*$"
)
_RE_NO_RANGE = re.compile(rf"^{_PARAM}\s+{_VALUE}{_UNIT}\s*$")

# Date detection
_RE_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_RE_US_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_DATE_KEYWORDS = ("collected", "drawn", "specimen", "report date", "date of service", "date:")


def _clean_param(raw: str) -> str:
    return raw.strip().strip(",").strip()


def parse_lab_values(text: str) -> tuple[list[LabValue], list[str]]:
    """Extract structured lab values and warnings from report text."""
    values: list[LabValue] = []
    warnings: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if m := _RE_NUMERIC.match(line):
            values.append(
                LabValue(
                    parameter=_clean_param(m["param"]),
                    value=float(m["value"]),
                    unit=m["unit"],
                    ref_low=float(m["low"]),
                    ref_high=float(m["high"]),
                    range_available=True,
                )
            )
        elif m := _RE_INEQUALITY.match(line):
            bound = float(m["bound"])
            # "<140" => normal is below 140 (upper bound); ">40" => lower bound.
            ref_low = bound if m["ineq"] == ">" else None
            ref_high = bound if m["ineq"] == "<" else None
            values.append(
                LabValue(
                    parameter=_clean_param(m["param"]),
                    value=float(m["value"]),
                    unit=m["unit"],
                    ref_low=ref_low,
                    ref_high=ref_high,
                    range_available=True,
                )
            )
        elif m := _RE_NO_RANGE.match(line):
            param = _clean_param(m["param"])
            values.append(
                LabValue(
                    parameter=param,
                    value=float(m["value"]),
                    unit=m["unit"],
                    ref_low=None,
                    ref_high=None,
                    range_available=False,
                )
            )
            warnings.append(f"Parameter '{param}' has no parseable reference range.")

    return values, warnings


def detect_report_date(text: str) -> date | None:
    """Best-effort extraction of the report/collection date from PDF text.

    Prefers dates on lines mentioning collection/report keywords, then falls
    back to the first date found anywhere. Returns None if nothing parses.
    """
    lines = text.splitlines()
    keyword_lines = [ln for ln in lines if any(k in ln.lower() for k in _DATE_KEYWORDS)]

    for line in (*keyword_lines, *lines):
        if found := _date_from_line(line):
            return found
    return None


def _date_from_line(line: str) -> date | None:
    if m := _RE_ISO_DATE.search(line):
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    if m := _RE_US_DATE.search(line):
        try:
            return date(int(m[3]), int(m[1]), int(m[2]))
        except ValueError:
            return None
    return None


def extract_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
