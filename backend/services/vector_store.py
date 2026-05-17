"""Pinecone serverless vector store with namespace isolation.

We embed locally with BGE (384-dim) and use Pinecone's raw vector API
(`upsert` / `query`) — *not* the integrated-embeddings `upsert_records` —
because we control the embedding model.

Namespaces are mandatory (see `.agents/PINECONE.md`): every upload gets
its own UUID namespace, ensuring zero cross-tenant leakage.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec

from backend.config import get_settings
from backend.services import embedder

logger = logging.getLogger(__name__)

_VECTOR_BATCH = 100
_INDEX_READY_TIMEOUT_S = 60


class VectorStore:
    """Thin async-friendly wrapper around Pinecone."""

    _instance: Optional["VectorStore"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        cfg = get_settings()
        self._cfg = cfg
        self._pc = Pinecone(api_key=cfg.PINECONE_API_KEY)
        self._index_name = cfg.PINECONE_INDEX_NAME
        self._dim = cfg.EMBEDDING_DIMENSION
        self._ensure_index()
        self._index = self._pc.Index(self._index_name)

    @classmethod
    def get(cls) -> "VectorStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_index(self) -> None:
        if self._pc.has_index(self._index_name):
            logger.info("Pinecone index '%s' already exists", self._index_name)
            return

        logger.info(
            "Creating Pinecone index '%s' (dim=%d, cosine, %s/%s)",
            self._index_name,
            self._dim,
            self._cfg.PINECONE_CLOUD,
            self._cfg.PINECONE_REGION,
        )
        self._pc.create_index(
            name=self._index_name,
            dimension=self._dim,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=self._cfg.PINECONE_CLOUD,
                region=self._cfg.PINECONE_REGION,
            ),
        )

        deadline = time.time() + _INDEX_READY_TIMEOUT_S
        while time.time() < deadline:
            desc = self._pc.describe_index(self._index_name)
            status = getattr(desc, "status", None) or {}
            ready = getattr(status, "ready", None)
            if ready is None and isinstance(status, dict):
                ready = status.get("ready", False)
            if ready:
                logger.info("Index ready")
                return
            time.sleep(2)
        raise RuntimeError("Pinecone index did not become ready in time")

    async def upsert_chunks(
        self,
        chunks: List[Document],
        namespace: str,
    ) -> int:
        if not chunks:
            return 0

        texts = [c.page_content for c in chunks]
        vectors_values = await embedder.embed_documents(texts)

        records: List[Dict[str, Any]] = []
        for chunk, values in zip(chunks, vectors_values):
            md = chunk.metadata or {}
            records.append(
                {
                    "id": f"{namespace}:{md.get('chunk_index', uuid.uuid4().hex)}",
                    "values": values,
                    "metadata": {
                        "text": chunk.page_content,
                        "source": str(md.get("source", "unknown")),
                        "page": int(md.get("page", 0) or 0),
                        "chunk_index": int(md.get("chunk_index", 0) or 0),
                    },
                }
            )

        for i in range(0, len(records), _VECTOR_BATCH):
            batch = records[i : i + _VECTOR_BATCH]
            await asyncio.to_thread(
                self._index.upsert,
                vectors=batch,
                namespace=namespace,
            )

        await asyncio.sleep(2.0)
        return len(records)

    async def query(
        self,
        query_text: str,
        namespace: str,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        k = top_k or self._cfg.RETRIEVAL_TOP_K
        vec = await embedder.embed_query(query_text)
        result = await asyncio.to_thread(
            self._index.query,
            vector=vec,
            top_k=k,
            namespace=namespace,
            include_metadata=True,
        )

        matches = getattr(result, "matches", None) or result.get("matches", [])
        out: List[Dict[str, Any]] = []
        for m in matches:
            md = getattr(m, "metadata", None) or m.get("metadata", {}) or {}
            score = getattr(m, "score", None)
            if score is None and isinstance(m, dict):
                score = m.get("score")
            out.append(
                {
                    "text": md.get("text", ""),
                    "source": md.get("source", "unknown"),
                    "page": int(md.get("page", 0) or 0),
                    "chunk_index": int(md.get("chunk_index", 0) or 0),
                    "score": float(score) if score is not None else 0.0,
                }
            )
        return out

    async def delete_namespace(self, namespace: str) -> None:
        await asyncio.to_thread(
            self._index.delete, delete_all=True, namespace=namespace
        )


def warmup() -> None:
    VectorStore.get()
