"""Ingestion orchestration: store the raw file, extract text with provenance,
persist Document + segments.

The AI structuring pipeline (Phase 2) reads these segments to generate courses;
the chatbot sync (Phase 4) embeds them into Qdrant with their source_ref.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.ingestion.db_models import Document, DocumentSegment
from app.components.ingestion.extractors import extract
from app.core.storage import get_storage

logger = logging.getLogger(__name__)


def _doc_code_from_name(filename: str, seq: int) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", filename.rsplit(".", 1)[0]).strip("-").upper()
    stem = stem[:24] or "DOC"
    return f"{stem}-{seq:02d}"


class IngestionService:
    @staticmethod
    async def ingest(
        *,
        data: bytes,
        filename: str,
        content_type: str | None,
        uploaded_by: int | None,
        db: AsyncSession,
    ) -> Document:
        # 1) extract text + provenance
        extracted = extract(data, filename=filename, content_type=content_type)

        # 2) store the raw file (MinIO / local)
        count = (await db.execute(select(func.count()).select_from(Document))).scalar_one()
        doc_code = _doc_code_from_name(filename, count + 1)
        storage = get_storage()
        storage_uri = storage.put(f"documents/{doc_code}/{filename}", data)

        # 3) persist Document + segments
        doc = Document(
            doc_code=doc_code,
            filename=filename,
            storage_uri=storage_uri,
            method=extracted.method,
            char_count=extracted.char_count,
            status="extracted",
            uploaded_by=uploaded_by,
        )
        for i, seg in enumerate(extracted.segments):
            doc.segments.append(
                DocumentSegment(ordinal=i, page=seg.page, section=seg.section, text=seg.text)
            )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        logger.info(
            "Ingested %s (%s) — %d chars, %d segments via %s",
            doc_code,
            filename,
            extracted.char_count,
            len(extracted.segments),
            extracted.method,
        )
        return doc

    @staticmethod
    async def get(doc_id: int, db: AsyncSession) -> Document | None:
        return await db.get(Document, doc_id)

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Document]:
        result = await db.execute(select(Document).order_by(Document.id))
        return list(result.scalars().all())
