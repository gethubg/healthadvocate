"""Application configuration loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed settings sourced from environment variables.

    Validated at startup so missing required secrets fail fast.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_embed_model: str = Field("text-embedding-3-small", alias="OPENAI_EMBED_MODEL")
    openai_llm_model: str = Field("gpt-4o", alias="OPENAI_LLM_MODEL")

    # Pinecone
    pinecone_api_key: str = Field(..., alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field("healthadvocate", alias="PINECONE_INDEX_NAME")

    # Storage
    pdf_storage_dir: Path = Field(Path("./data/pdfs"), alias="PDF_STORAGE_DIR")
    sqlite_path: Path = Field(Path("./data/healthadvocate.db"), alias="SQLITE_PATH")

    # API
    cors_origins: str = Field("http://localhost:5173", alias="CORS_ORIGINS")
    max_upload_mb: int = Field(20, alias="MAX_UPLOAD_MB")

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS is a comma-separated string; expose it as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_dirs(self) -> None:
        """Create local storage directories if they do not exist."""
        self.pdf_storage_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor used as a FastAPI dependency."""
    return Settings()  # type: ignore[call-arg]
