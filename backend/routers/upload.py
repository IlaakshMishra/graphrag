"""POST /upload — ingest a document, return its private namespace."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.models.upload import UploadResponse
from backend.services import document_parser
from backend.services.entity_extractor import extract_entities_from_chunk
from backend.services.graph_store import get_graph_store
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

    extraction_results = await asyncio.gather(
        *[extract_entities_from_chunk(doc.page_content) for doc in chunks],
        return_exceptions=True,
    )

    all_entities: list[dict] = []
    all_relations: list[dict] = []
    for result in extraction_results:
        if isinstance(result, dict):
            all_entities.extend(result.get("entities", []))
            all_relations.extend(result.get("relationships", []))

    seen_names: set[str] = set()
    unique_entities: list[dict] = []
    for e in all_entities:
        if e.get("name") and e["name"] not in seen_names:
            seen_names.add(e["name"])
            unique_entities.append(e)

    entities_indexed = 0
    if unique_entities:
        try:
            graph_store = await get_graph_store()
            entities_indexed = await asyncio.to_thread(
                graph_store.upsert_entities, unique_entities, all_relations, namespace
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("graph store upsert failed for ns=%s: %s", namespace, exc)

    return UploadResponse(
        namespace=namespace,
        filename=file.filename,
        chunks_indexed=indexed,
        bytes_processed=len(raw),
        entities_indexed=entities_indexed,
    )
