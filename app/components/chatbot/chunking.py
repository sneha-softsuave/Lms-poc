"""Chunking with provenance carry-through.

Splits content into ~CHUNK_SIZE character chunks (boundary-aware via langchain's
recursive splitter when available; simple fallback otherwise). Each chunk keeps
its parent's source_ref so retrieved context can cite {doc, section, page}.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _split(text: str, size: int, overlap: int) -> list[str]:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
        return [c for c in splitter.split_text(text) if c.strip()]
    except Exception:
        # Fallback: fixed windows with overlap.
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start : start + size])
            start += max(1, size - overlap)
        return [c for c in chunks if c.strip()]


def chunk_content(text: str, metadata: dict[str, Any]) -> list[Chunk]:
    if not text.strip():
        return []
    parts = _split(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    return [Chunk(text=p, metadata={**metadata, "chunk_index": i}) for i, p in enumerate(parts)]
