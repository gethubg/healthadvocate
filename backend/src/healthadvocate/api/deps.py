"""FastAPI dependency providers.

Each service is built from settings here so routes stay thin and tests can
override any provider via ``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache

from healthadvocate.advisor.food_advisor import FoodAdvisor, build_default_advisor
from healthadvocate.config import Settings, get_settings
from healthadvocate.ingestion.extraction import LabExtractor, build_default_extractor
from healthadvocate.ingestion.indexer import Indexer
from healthadvocate.ingestion.pdf_store import PdfStore
from healthadvocate.retrieval.query_engine import BloodworkQueryEngine
from healthadvocate.retrieval.synthesis import LlamaIndexResponder
from healthadvocate.storage.lab_store import LabStore


@lru_cache
def get_lab_store() -> LabStore:
    return LabStore(get_settings().sqlite_path)


@lru_cache
def get_pdf_store() -> PdfStore:
    return PdfStore(get_settings().pdf_storage_dir)


def get_indexer() -> Indexer:
    return Indexer(get_lab_store(), get_settings())


def get_query_engine() -> BloodworkQueryEngine:
    settings: Settings = get_settings()
    return BloodworkQueryEngine(get_lab_store(), LlamaIndexResponder(settings))


def get_food_advisor() -> FoodAdvisor:
    return build_default_advisor(get_settings())


def get_lab_extractor() -> LabExtractor:
    return build_default_extractor(get_settings())
