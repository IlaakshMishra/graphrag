"""Application configuration loaded from environment variables.

All secrets and tunable values live here. The app fails loudly on startup
if any required variable is missing, which is the desired behaviour for a
production-style template.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            PROJECT_ROOT / ".env",
            PROJECT_ROOT.parent / ".env",
        ],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    OPENAI_API_KEY: str = Field(..., description="OpenAI key for chat + grading")
    OPENAI_CHAT_MODEL: str = Field("gpt-4o", description="Generation model")
    OPENAI_GRADER_MODEL: str = Field(
        "gpt-4o-mini",
        description="Cheap model for relevance grading; gpt-4o also works",
    )

    PINECONE_API_KEY: str = Field(..., description="Pinecone serverless key")
    PINECONE_INDEX_NAME: str = Field("rag-eval-index")
    PINECONE_CLOUD: str = Field("aws")
    PINECONE_REGION: str = Field("us-east-1")

    HUGGINGFACE_MODEL: str = Field("BAAI/bge-small-en-v1.5")
    EMBEDDING_DIMENSION: int = Field(384)

    APP_HOST: str = Field("0.0.0.0")
    APP_PORT: int = Field(8000)
    CORS_ORIGINS: str = Field("http://localhost:5173")

    CHUNK_SIZE: int = Field(512)
    CHUNK_OVERLAP: int = Field(64)
    RETRIEVAL_TOP_K: int = Field(
        8,
        ge=1,
        le=50,
        description="More chunks helps diagram/OCR-heavy PDFs (dense retrieval)",
    )
    HISTORY_WINDOW: int = Field(5)
    # When the relevance grader drops every chunk (common with noisy OCR), still pass top retrieval hits.
    GRADER_FALLBACK_TOP_N: int = Field(
        4,
        ge=1,
        le=20,
        description="If grader keeps zero chunks, inject this many highest-ranked retrieved chunks",
    )

    # Neo4j
    NEO4J_URI: str = Field("bolt://localhost:7687")
    NEO4J_USER: str = Field("neo4j")
    NEO4J_PASSWORD: str = Field("password123")

    # Graph retrieval
    GRAPH_RETRIEVAL_HOPS: int = Field(default=2, ge=1, le=5)
    GRAPH_MAX_ENTITIES: int = Field(10)

    # OCR (Tesseract). GUI/Cursor often lacks Homebrew PATH — set TESSERACT_CMD explicitly.
    DOCUMENT_OCR_ENABLED: bool = Field(
        True,
        description="When True, run Tesseract on images and PDF page renders",
    )
    TESSERACT_CMD: Optional[str] = Field(
        None,
        description="Absolute path to tesseract binary, e.g. /opt/homebrew/bin/tesseract",
    )
    # Vector diagrams have no embedded JPEG/PNG — rasterize the page and OCR (no vision LLM).
    PDF_PAGE_RENDER_OCR: bool = Field(
        True,
        description="When embedded-image OCR is weak or absent, rasterize page and OCR",
    )
    PDF_PAGE_OCR_DPI: int = Field(
        200,
        ge=72,
        le=400,
        description="Resolution for full-page OCR — raise to 250–300 for tiny diagram fonts",
    )
    PDF_MIN_EMBEDDED_OCR_CHARS: int = Field(
        40,
        ge=0,
        description="If embedded bitmap OCR yields fewer chars than this, also run page-render OCR",
    )
    # Academic PDFs: caption says “Figure N” but diagram text is vector-only → force page OCR.
    PDF_PAGE_OCR_ON_FIGURE_CAPTION: bool = Field(
        True,
        description="If page text mentions Figure/Fig., always run full-page OCR for diagram labels",
    )
    PDF_PAGE_OCR_SECOND_PASS: bool = Field(
        True,
        description="Run two Tesseract layouts (sparse + block) and merge — helps diagram callouts",
    )
    OCR_TESSERACT_CONFIG_IMAGE: str = Field(
        "--oem 3 --psm 3",
        description="Tesseract args for embedded PNG/JPEG in PDFs",
    )
    OCR_TESSERACT_CONFIG_PAGE: str = Field(
        "--oem 3 --psm 11",
        description="Sparse text / diagrams (Tesseract page segmentation mode 11)",
    )
    OCR_TESSERACT_CONFIG_PAGE_BLOCK: str = Field(
        "--oem 3 --psm 6",
        description="Second pass: assume uniform text block — catches boxed labels in figures",
    )

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _strip_origins(cls, v: str) -> str:
        return v.strip()

    @field_validator("TESSERACT_CMD", mode="before")
    @classmethod
    def _strip_tesseract_cmd(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip().strip('"').strip("'")
        return s if s else None

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
