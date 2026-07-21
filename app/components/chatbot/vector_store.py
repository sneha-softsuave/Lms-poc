"""Pluggable vector store for the chatbot's retrieval.

Two backends behind one interface (mirrors ThinkArguments' Qdrant service, with
access-control filtering applied BEFORE search, not after):

- ``QdrantVectorStore``  — production / docker-compose (VECTOR_BACKEND=qdrant)
- ``InMemoryVectorStore`` — dev + tests, no external service (VECTOR_BACKEND=memory)

Vectors are produced by the model gateway (embed), so the store only stores +
searches — it never imports an embedding SDK.
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    score: float
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(Protocol):
    def ensure(self, dim: int) -> None: ...
    def delete_by_content(self, content_type: str, content_id: int) -> None: ...
    def upsert(self, vectors: list[list[float]], texts: list[str], metadatas: list[dict]) -> list[str]: ...
    def search(self, vector: list[float], *, course_id: int, top_k: int) -> list[SearchHit]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class InMemoryVectorStore:
    """Simple cosine store. Access control = filter by course_id before scoring."""

    def __init__(self) -> None:
        self._points: dict[str, dict] = {}

    def ensure(self, dim: int) -> None:  # no-op
        pass

    def delete_by_content(self, content_type: str, content_id: int) -> None:
        drop = [
            pid
            for pid, p in self._points.items()
            if p["metadata"].get("content_type") == content_type
            and p["metadata"].get("content_id") == content_id
        ]
        for pid in drop:
            del self._points[pid]

    def upsert(self, vectors, texts, metadatas) -> list[str]:
        ids = []
        for vec, text, meta in zip(vectors, texts, metadatas, strict=True):
            pid = uuid.uuid4().hex
            self._points[pid] = {"vector": vec, "text": text, "metadata": meta}
            ids.append(pid)
        return ids

    def search(self, vector, *, course_id, top_k) -> list[SearchHit]:
        scored = [
            SearchHit(_cosine(vector, p["vector"]), p["text"], p["metadata"])
            for p in self._points.values()
            if p["metadata"].get("course_id") == course_id  # access control BEFORE ranking
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]


class QdrantVectorStore:
    def __init__(self, url: str, api_key: str | None, collection: str = "defense_lms_kb") -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=url, api_key=api_key or None)
        self.collection = collection
        self._dim: int | None = None

    def ensure(self, dim: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        self._dim = dim
        try:
            self.client.get_collection(self.collection)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def delete_by_content(self, content_type: str, content_id: int) -> None:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(key="content_type", match=MatchValue(value=content_type)),
                    FieldCondition(key="content_id", match=MatchValue(value=content_id)),
                ]
            ),
        )

    def upsert(self, vectors, texts, metadatas) -> list[str]:
        from qdrant_client.models import PointStruct

        points, ids = [], []
        for vec, text, meta in zip(vectors, texts, metadatas, strict=True):
            pid = uuid.uuid4().hex
            payload = {**meta, "text": text}
            points.append(PointStruct(id=pid, vector=vec, payload=payload))
            ids.append(pid)
        self.client.upsert(collection_name=self.collection, points=points)
        return ids

    def search(self, vector, *, course_id, top_k) -> list[SearchHit]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=Filter(
                must=[FieldCondition(key="course_id", match=MatchValue(value=course_id))]
            ),
            limit=top_k,
        )
        return [
            SearchHit(r.score, r.payload.get("text", ""), {k: v for k, v in r.payload.items() if k != "text"})
            for r in results
        ]


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is not None:
        return _store
    backend = (settings.VECTOR_BACKEND or "memory").lower()
    if backend == "qdrant":
        try:
            _store = QdrantVectorStore(settings.QDRANT_URL, settings.QDRANT_API_KEY)
            logger.info("Vector backend: Qdrant (%s)", settings.QDRANT_URL)
            return _store
        except Exception as exc:  # noqa: BLE001
            logger.warning("Qdrant unavailable (%s) — falling back to in-memory store", exc)
    _store = InMemoryVectorStore()
    logger.info("Vector backend: in-memory")
    return _store


def reset_vector_store() -> None:
    """Test helper — drop the singleton so each run starts clean."""
    global _store
    _store = None
