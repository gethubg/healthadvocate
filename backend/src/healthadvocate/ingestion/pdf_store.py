"""Filesystem persistence for uploaded bloodwork PDFs.

Responsible only for storing/retrieving the raw PDF bytes and minting a stable
`report_id`. Report *metadata* (date, upload time) lives in the lab_store; this
module just owns the files on disk.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredPdf:
    """Result of persisting an uploaded PDF."""

    report_id: str
    filename: str
    path: Path


class PdfStore:
    def __init__(self, storage_dir: str | Path) -> None:
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _new_report_id() -> str:
        return f"rpt_{uuid.uuid4().hex[:12]}"

    def path_for(self, report_id: str) -> Path:
        return self._dir / f"{report_id}.pdf"

    def save(self, filename: str, content: bytes) -> StoredPdf:
        """Persist PDF bytes under a freshly minted report_id."""
        report_id = self._new_report_id()
        path = self.path_for(report_id)
        path.write_bytes(content)
        return StoredPdf(report_id=report_id, filename=filename, path=path)

    def read(self, report_id: str) -> bytes:
        path = self.path_for(report_id)
        if not path.exists():
            raise FileNotFoundError(f"No stored PDF for report_id={report_id}")
        return path.read_bytes()

    def delete(self, report_id: str) -> None:
        self.path_for(report_id).unlink(missing_ok=True)
