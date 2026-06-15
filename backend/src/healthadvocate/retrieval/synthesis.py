"""Answer synthesis over the vector index.

The ``Responder`` protocol is the injectable boundary between orchestration
(query_engine) and the networked LlamaIndex/OpenAI/Pinecone stack — so the
query engine can be unit-tested with a fake responder.

``LlamaIndexResponder`` is the real implementation. It scopes retrieval to a
single report via a ``report_id`` metadata filter, so answers are grounded only
in the report the caller selected (the latest, per query_engine).
"""

from __future__ import annotations

from typing import Protocol

from healthadvocate.config import Settings


class Responder(Protocol):
    """Answers a question grounded in one report's chunks."""

    def answer(self, question: str, report_id: str) -> str: ...


class LlamaIndexResponder:
    """Real retrieval + synthesis via LlamaIndex over Pinecone."""

    def __init__(self, settings: Settings, top_k: int = 5) -> None:
        self._settings = settings
        self._top_k = top_k

    def answer(self, question: str, report_id: str) -> str:
        from llama_index.core import Settings as LISettings
        from llama_index.core import VectorStoreIndex
        from llama_index.core.vector_stores import (
            ExactMatchFilter,
            MetadataFilters,
        )
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.llms.openai import OpenAI
        from llama_index.vector_stores.pinecone import PineconeVectorStore
        from pinecone import Pinecone

        s = self._settings
        pc = Pinecone(api_key=s.pinecone_api_key)
        vector_store = PineconeVectorStore(pinecone_index=pc.Index(s.pinecone_index_name))

        LISettings.embed_model = OpenAIEmbedding(
            model=s.openai_embed_model, api_key=s.openai_api_key
        )
        LISettings.llm = OpenAI(model=s.openai_llm_model, api_key=s.openai_api_key)

        index = VectorStoreIndex.from_vector_store(vector_store)
        query_engine = index.as_query_engine(
            similarity_top_k=self._top_k,
            filters=MetadataFilters(
                filters=[ExactMatchFilter(key="report_id", value=report_id)]
            ),
        )
        return str(query_engine.query(question))
