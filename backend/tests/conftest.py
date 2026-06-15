"""Shared test fixtures and environment setup.

Sets dummy secrets so Settings validation passes without real credentials.
"""

from __future__ import annotations

import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")
os.environ.setdefault("PDF_STORAGE_DIR", "./data/test_pdfs")
os.environ.setdefault("SQLITE_PATH", "./data/test.db")
