"""HuggingFace BGE embedding wrapper.

The BGE family ships with an instruction-tuning convention: queries are
prefixed with a short instruction, while passages (documents) are embedded
as-is. Skipping the prefix on queries silently degrades recall — see
https://huggingface.co/BAAI/bge-small-en-v1.5
"""

from __future__ import annotations

import asyncio
import threading
from typing import List, Optional

from sentence_transformers import SentenceTransformer

from backend.config import get_settings

_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class _Embedder:
    """Process-wide singleton wrapping a sentence-transformers model."""

    _instance: Optional["_Embedder"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        cfg = get_settings()
        self._model_name = cfg.HUGGINGFACE_MODEL
        self._dim = cfg.EMBEDDING_DIMENSION
        self._model = SentenceTransformer(self._model_name)

    @classmethod
    def get(cls) -> "_Embedder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> List[float]:
        prefixed = f"{_BGE_QUERY_PREFIX}{text}"
        vec = self._model.encode(
            prefixed,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vec.tolist()


def warmup() -> None:
    _Embedder.get()


async def embed_documents(texts: List[str]) -> List[List[float]]:
    return await asyncio.to_thread(_Embedder.get().embed_documents, texts)


async def embed_query(text: str) -> List[float]:
    return await asyncio.to_thread(_Embedder.get().embed_query, text)


def embedding_dimension() -> int:
    return _Embedder.get().dimension
