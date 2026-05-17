"""POST /chat — conversational RAG query against an uploaded namespace."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.models.chat import ChatRequest, ChatResponse, SourceCitation
from backend.services import rag_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = await rag_graph.run_rag(
            question=req.question,
            chat_history=[turn.model_dump() for turn in req.chat_history],
            namespace=req.namespace,
            session_id=req.session_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("RAG failure for ns=%s", req.namespace)
        raise HTTPException(status_code=500, detail=f"rag error: {exc}") from exc

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceCitation(**s) for s in result.get("sources", [])],
        session_id=result["session_id"],
        namespace=result["namespace"],
        used_documents=result.get("used_documents", 0),
    )
