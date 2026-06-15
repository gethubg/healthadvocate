"""Index an ingested report into both stores.

Writes structured rows to the SQLite lab_store and embeds the report text into
Pinecone via LlamaIndex. The vector path is injectable (``vector_writer``) so
tests can run without OpenAI/Pinecone network calls.
"""

from __future__ import annotations

from collections.abc import Callable

from healthadvocate.config import Settings
from healthadvocate.models import LabValue, Report
from healthadvocate.storage.lab_store import LabStore

VectorWriter = Callable[[Report, str], None]
VectorDeleter = Callable[[str], None]


class Indexer:
    def __init__(
        self,
        lab_store: LabStore,
        settings: Settings,
        vector_writer: VectorWriter | None = None,
        vector_deleter: VectorDeleter | None = None,
    ) -> None:
        self._lab_store = lab_store
        self._settings = settings
        self._vector_writer = vector_writer or self._default_vector_writer
        self._vector_deleter = vector_deleter or self._default_vector_deleter

    def index_report(self, report: Report, text: str, values: list[LabValue]) -> None:
        """Persist structured rows, then embed text into the vector store.

        Structured rows are written first: they power deterministic analysis and
        trends, and must not be lost if the (networked) vector step fails.
        """
        self._lab_store.save_report(report, values)
        self._vector_writer(report, text)

    def delete_vectors(self, report_id: str) -> None:
        """Remove a report's vectors from the index (best-effort, networked)."""
        self._vector_deleter(report_id)

    def _default_vector_deleter(self, report_id: str) -> None:
        from pinecone import Pinecone

        s = self._settings
        pc = Pinecone(api_key=s.pinecone_api_key)
        pc.Index(s.pinecone_index_name).delete(filter={"report_id": report_id})

    def _default_vector_writer(self, report: Report, text: str) -> None:
        """Real LlamaIndex → Pinecone path. Imports are local to keep the module
        importable (and unit-testable) without the heavy optional deps loaded."""
        from llama_index.core import (
            Document,
            StorageContext,
            VectorStoreIndex,
        )
        from llama_index.core import (
            Settings as LISettings,
        )
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.vector_stores.pinecone import PineconeVectorStore
        from pinecone import Pinecone

        s = self._settings
        pc = Pinecone(api_key=s.pinecone_api_key)
        pinecone_index = pc.Index(s.pinecone_index_name)
        vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        LISettings.embed_model = OpenAIEmbedding(
            model=s.openai_embed_model, api_key=s.openai_api_key
        )

        document = Document(
            text=text,
            doc_id=report.report_id,
            metadata={
                "report_id": report.report_id,
                "report_date": report.report_date.isoformat(),
                "uploaded_at": report.uploaded_at.isoformat(),
                "filename": report.filename,
            },
        )
        VectorStoreIndex.from_documents([document], storage_context=storage_context)
