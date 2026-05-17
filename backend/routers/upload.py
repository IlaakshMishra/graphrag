"""POST /upload — ingest a document, return its private namespace."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.models.upload import UploadResponse
from backend.services import document_parser
from backend.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

_MAX_BYTES = 25 * 1024 * 1024
_ALLOWED_EXT = {
    ".pdf",
    ".txt",
    ".md",
    ".docx",
    ".xlsx",
    ".xls",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
}


@router.post("", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=422, detail="filename missing")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in _ALLOWED_EXT:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported extension '{ext}'. Allowed: {sorted(_ALLOWED_EXT)}",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="empty file")
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds 25MB limit")

    try:
        chunks = document_parser.parse(raw, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("parse failure for %s", file.filename)
        raise HTTPException(status_code=500, detail=f"parse error: {exc}") from exc

    if not chunks:
        raise HTTPException(status_code=422, detail="document produced zero chunks")

    namespace = f"upload-{uuid.uuid4().hex[:12]}"

    try:
        indexed = await VectorStore.get().upsert_chunks(chunks, namespace=namespace)
    except Exception as exc:  # noqa: BLE001
        logger.exception("upsert failure for ns=%s", namespace)
        raise HTTPException(status_code=500, detail=f"vector store error: {exc}") from exc

    return UploadResponse(
        namespace=namespace,
        filename=file.filename,
        chunks_indexed=indexed,
        bytes_processed=len(raw),
    )
