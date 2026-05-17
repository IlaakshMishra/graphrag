"""Upload response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    namespace: str
    filename: str
    chunks_indexed: int = Field(..., ge=0)
    bytes_processed: int = Field(..., ge=0)
