"""Orchestrates question answering against the latest report.

"Latest" = the report with the maximum ``report_date`` (``uploaded_at`` as
tiebreaker), resolved from the lab_store. Retrieval/synthesis is delegated to a
``Responder`` scoped to that report, keeping the network behind an injectable
boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from healthadvocate.models import Report
from healthadvocate.retrieval.synthesis import Responder
from healthadvocate.storage.lab_store import LabStore


class NoReportsError(Exception):
    """Raised when a question is asked before any report has been uploaded."""


@dataclass(frozen=True)
class QueryResult:
    answer: str
    report: Report


class BloodworkQueryEngine:
    def __init__(self, lab_store: LabStore, responder: Responder) -> None:
        self._lab_store = lab_store
        self._responder = responder

    def ask(self, question: str) -> QueryResult:
        """Answer a question grounded in the latest report.

        Raises NoReportsError if no reports exist yet.
        """
        latest = self._lab_store.get_latest_report()
        if latest is None:
            raise NoReportsError("No reports have been uploaded yet.")

        answer = self._responder.answer(question, latest.report_id)
        return QueryResult(answer=answer, report=latest)
