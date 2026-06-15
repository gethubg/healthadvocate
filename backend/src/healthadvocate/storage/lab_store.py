"""SQLite access layer for structured bloodwork data.

This store is the source of truth for:
  * report metadata (used to resolve the "latest" report by report_date), and
  * structured lab values (used by the analyzer and the /trends endpoint).

It is deliberately separate from the Pinecone vector index: semantic Q&A lives
in Pinecone; exact, ordered, filterable numeric queries live here.

All dates are persisted as ISO-8601 strings (`YYYY-MM-DD` for dates,
full ISO for timestamps) so they sort lexicographically in SQL.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from healthadvocate.labs.analyzer import is_abnormal
from healthadvocate.models import LabValue, Report, TrendPoint, TrendSeries

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    report_id   TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    report_date TEXT NOT NULL,   -- ISO YYYY-MM-DD (authoritative recency key)
    uploaded_at TEXT NOT NULL    -- ISO timestamp (tiebreaker)
);

CREATE TABLE IF NOT EXISTS lab_values (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id       TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    parameter       TEXT NOT NULL,
    parameter_norm  TEXT NOT NULL,   -- lowercased for case-insensitive lookup
    value           REAL NOT NULL,
    unit            TEXT,
    ref_low         REAL,
    ref_high        REAL,
    range_available INTEGER NOT NULL  -- 0/1
);

CREATE INDEX IF NOT EXISTS idx_lab_values_param ON lab_values(parameter_norm);
CREATE INDEX IF NOT EXISTS idx_lab_values_report ON lab_values(report_id);
CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(report_date, uploaded_at);
"""


class LabStore:
    """Thin, synchronous SQLite wrapper. One instance per database file."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------ writes

    def save_report(self, report: Report, values: list[LabValue]) -> None:
        """Insert a report and its lab values atomically.

        Re-saving an existing report_id replaces its rows (idempotent ingestion).
        """
        with self._connect() as conn:
            conn.execute("DELETE FROM reports WHERE report_id = ?", (report.report_id,))
            conn.execute(
                "INSERT INTO reports (report_id, filename, report_date, uploaded_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    report.report_id,
                    report.filename,
                    report.report_date.isoformat(),
                    report.uploaded_at.isoformat(),
                ),
            )
            conn.executemany(
                "INSERT INTO lab_values "
                "(report_id, parameter, parameter_norm, value, unit, ref_low, ref_high, "
                "range_available) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        report.report_id,
                        v.parameter,
                        v.parameter.strip().lower(),
                        v.value,
                        v.unit,
                        v.ref_low,
                        v.ref_high,
                        1 if v.range_available else 0,
                    )
                    for v in values
                ],
            )

    # ------------------------------------------------------------------- reads

    def list_reports(self) -> list[Report]:
        """All reports, most recent first (report_date desc, uploaded_at desc)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT report_id, filename, report_date, uploaded_at FROM reports "
                "ORDER BY report_date DESC, uploaded_at DESC"
            ).fetchall()
        return [self._row_to_report(r) for r in rows]

    def get_latest_report(self) -> Report | None:
        """Resolve the latest report: max(report_date), uploaded_at as tiebreaker."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT report_id, filename, report_date, uploaded_at FROM reports "
                "ORDER BY report_date DESC, uploaded_at DESC LIMIT 1"
            ).fetchone()
        return self._row_to_report(row) if row else None

    def get_values_for_report(self, report_id: str) -> list[LabValue]:
        """All structured lab values for a single report."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT parameter, value, unit, ref_low, ref_high, range_available "
                "FROM lab_values WHERE report_id = ? ORDER BY parameter",
                (report_id,),
            ).fetchall()
        return [self._row_to_lab_value(r) for r in rows]

    def get_trend(
        self,
        parameter: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> TrendSeries | None:
        """Time series for one parameter across reports, ordered by report_date.

        Returns None if the parameter is not present in any report.
        """
        clauses = ["lv.parameter_norm = ?"]
        params: list[object] = [parameter.strip().lower()]
        if date_from is not None:
            clauses.append("r.report_date >= ?")
            params.append(date_from.isoformat())
        if date_to is not None:
            clauses.append("r.report_date <= ?")
            params.append(date_to.isoformat())
        where = " AND ".join(clauses)

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT lv.parameter, lv.value, lv.unit, lv.ref_low, lv.ref_high, "  # noqa: S608
                f"lv.range_available, r.report_date "
                f"FROM lab_values lv JOIN reports r ON lv.report_id = r.report_id "
                f"WHERE {where} ORDER BY r.report_date ASC, r.uploaded_at ASC",
                params,
            ).fetchall()

        if not rows:
            return None

        points = [
            TrendPoint(
                report_date=date.fromisoformat(r["report_date"]),
                value=r["value"],
                ref_low=r["ref_low"],
                ref_high=r["ref_high"],
                abnormal=is_abnormal(
                    r["value"], r["ref_low"], r["ref_high"], bool(r["range_available"])
                ),
            )
            for r in rows
        ]
        return TrendSeries(
            parameter=rows[0]["parameter"],
            unit=rows[0]["unit"],
            points=points,
        )

    def delete_report(self, report_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))

    # -------------------------------------------------------------- converters

    @staticmethod
    def _row_to_report(row: sqlite3.Row) -> Report:
        return Report(
            report_id=row["report_id"],
            filename=row["filename"],
            report_date=date.fromisoformat(row["report_date"]),
            uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
        )

    @staticmethod
    def _row_to_lab_value(row: sqlite3.Row) -> LabValue:
        return LabValue(
            parameter=row["parameter"],
            value=row["value"],
            unit=row["unit"],
            ref_low=row["ref_low"],
            ref_high=row["ref_high"],
            range_available=bool(row["range_available"]),
        )
