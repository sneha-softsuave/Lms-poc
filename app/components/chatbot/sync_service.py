"""Sync published course content into the vector store (PRD 4.8 index step).

For each lesson and glossary term of a course: chunk -> embed (via gateway) ->
upsert into the vector store with course_id (for access-control filtering) and
source_ref (for citations). Change detection via SHA256 so re-sync only touches
modified content — mirrors ThinkArguments' sync_service pattern.
"""

from __future__ import annotations

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.chatbot.chunking import chunk_content
from app.components.chatbot.db_models import KbContent
from app.components.chatbot.vector_store import get_vector_store
from app.components.content.db_models import GlossaryTerm, Lesson, Module
from app.gateway.base import ModelGateway

logger = logging.getLogger(__name__)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SyncService:
    @staticmethod
    async def rebuild_published(gateway: ModelGateway, db: AsyncSession) -> dict:
        """Force-reindex every published course.

        Used on startup with the in-memory vector backend: the index lives in the
        server process and is empty after a restart, while the KbContent hash
        table (persisted) would otherwise make a normal sync skip everything. So
        we force a rebuild, ignoring the hash cache.
        """
        from app.components.content.db_models import STATUS_PUBLISHED, Course

        ids = (
            await db.execute(select(Course.id).where(Course.status == STATUS_PUBLISHED))
        ).scalars().all()
        total = {"courses": 0, "synced": 0}
        for cid in ids:
            stats = await SyncService.sync_course(cid, gateway, db, force=True)
            total["courses"] += 1
            total["synced"] += stats["synced"]
        return total

    @staticmethod
    async def sync_course(
        course_id: int, gateway: ModelGateway, db: AsyncSession, *, force: bool = False
    ) -> dict:
        store = get_vector_store()
        store.ensure(gateway.embedding_dim)
        stats = {"synced": 0, "skipped": 0, "force": force}

        # lessons
        lessons = (
            await db.execute(
                select(Lesson)
                .join(Module, Module.id == Lesson.module_id)
                .where(Module.course_id == course_id)
            )
        ).scalars().all()
        for lesson in lessons:
            body = f"{lesson.title}\n{lesson.body}"
            await SyncService._sync_item(
                db, store, gateway, "lesson", lesson.id, course_id, body,
                base_meta={"title": lesson.title, "source_ref": lesson.source_ref,
                           "lesson_id": lesson.id}, stats=stats, force=force,
            )

        # glossary
        terms = (
            await db.execute(select(GlossaryTerm).where(GlossaryTerm.course_id == course_id))
        ).scalars().all()
        for term in terms:
            body = f"{term.term}: {term.definition}"
            await SyncService._sync_item(
                db, store, gateway, "glossary", term.id, course_id, body,
                base_meta={"title": term.term, "source_ref": term.source_ref}, stats=stats,
                force=force,
            )

        await db.commit()
        logger.info("Synced course %d: %s", course_id, stats)
        return stats

    @staticmethod
    async def _sync_item(
        db, store, gateway, content_type, content_id, course_id, text, *, base_meta, stats,
        force: bool = False,
    ) -> None:
        h = _hash(text)
        existing = (
            await db.execute(
                select(KbContent).where(
                    KbContent.content_type == content_type, KbContent.content_id == content_id
                )
            )
        ).scalar_one_or_none()
        if existing and existing.content_hash == h and not force:
            stats["skipped"] += 1
            return

        if existing:
            store.delete_by_content(content_type, content_id)

        chunks = chunk_content(
            text,
            {**base_meta, "content_type": content_type, "content_id": content_id, "course_id": course_id},
        )
        if not chunks:
            return
        vectors = await gateway.embed([c.text for c in chunks])
        vector_ids = store.upsert(vectors, [c.text for c in chunks], [c.metadata for c in chunks])

        if existing:
            existing.content_hash = h
            existing.vector_ids = vector_ids
        else:
            db.add(
                KbContent(
                    content_type=content_type,
                    content_id=content_id,
                    course_id=course_id,
                    content_hash=h,
                    vector_ids=vector_ids,
                )
            )
        stats["synced"] += 1
