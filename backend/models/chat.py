"""Chat request/response schemas."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    namespace: str = Field(..., description="Pinecone namespace from /upload")
    session_id: str = Field(..., description="Client-generated UUID per chat session")
    chat_history: List[ChatTurn] = Field(default_factory=list)


class SourceCitation(BaseModel):
    source: str
    page: Optional[int] = None
    chunk_index: Optional[int] = None
    score: Optional[float] = None
    snippet: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation] = Field(default_factory=list)
    session_id: str
    namespace: str
    used_documents: int = 0
