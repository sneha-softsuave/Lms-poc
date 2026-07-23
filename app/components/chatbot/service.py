"""Grounded doubt-clearing chatbot (PRD 4.5) + component explainer (4.4.2).

Flow: embed query (gateway) -> access-filtered retrieval (course_id) -> if top
score < ABSTAIN_THRESHOLD, abstain (grounded=false, answer=null, related
lessons); else answer from retrieved context via the gateway, with citations
drawn from the chunks' source_refs. Lesson-aware: the active lesson is passed as
context AND boosts its own chunks when ranking. Multi-turn: messages persist per
thread and the last few exchanges are replayed into the prompt so follow-ups
resolve (retrieval still embeds the raw question — see _history).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.chatbot.db_models import ChatMessage, ChatThread
from app.components.chatbot.prompts import TUTOR_SYSTEM_PROMPT, build_tutor_prompt
from app.components.chatbot.vector_store import get_vector_store
from app.components.content.db_models import Lesson
from app.components.enrolment.service import EnrolmentService
from app.core.config import settings
from app.gateway.base import ModelGateway

logger = logging.getLogger(__name__)


def _dedupe_citations(hits) -> list[dict]:
    seen, out = set(), []
    for h in hits:
        ref = h.metadata.get("source_ref")
        if not ref:
            continue
        key = (ref.get("doc"), ref.get("section"), ref.get("page"))
        if key not in seen:
            seen.add(key)
            out.append(ref)
    return out


class ChatbotService:
    @staticmethod
    async def _resolve_thread(
        user_id: int, course_id: int, thread_id: int | None, db: AsyncSession
    ) -> ChatThread:
        if thread_id is not None:
            thread = await db.get(ChatThread, thread_id)
            if not thread or thread.user_id != user_id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found")
            return thread
        thread = ChatThread(user_id=user_id, course_id=course_id)
        db.add(thread)
        await db.flush()
        return thread

    @staticmethod
    async def answer(
        *,
        user_id: int,
        is_admin: bool,
        course_id: int,
        lesson_id: int | None,
        question: str,
        thread_id: int | None,
        gateway: ModelGateway,
        db: AsyncSession,
        source_top_k: int | None = None,
    ) -> dict:
        # Access control: learner must be enrolled (admins exempt).
        if not is_admin:
            enrolment = await EnrolmentService._get_enrolment(user_id, course_id, db)
            if not enrolment:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Enrol in the course to ask questions")

        thread = await ChatbotService._resolve_thread(user_id, course_id, thread_id, db)
        # Read history BEFORE recording this turn, so the new question is not in it.
        history = await ChatbotService._history(thread.id, db)
        db.add(ChatMessage(thread_id=thread.id, role="user", content=question))

        # Retrieve (access-filtered by course_id BEFORE ranking). Two pools: the
        # reviewed course material leads, the raw source document supplements it —
        # see _retrieve.
        store = get_vector_store()
        query_vec = (await gateway.embed([question]))[0]
        course_hits, source_hits = ChatbotService._retrieve(
            store, query_vec, course_id, source_top_k, lesson_id=lesson_id
        )
        hits = course_hits + source_hits
        top_score = max((h.score for h in hits), default=0.0)

        lesson_context = None
        if lesson_id is not None:
            lesson = await db.get(Lesson, lesson_id)
            if lesson:
                lesson_context = f"{lesson.title}: {lesson.body}"

        # Abstain when nothing is sufficiently relevant.
        if not hits or top_score < settings.ABSTAIN_THRESHOLD:
            related = await ChatbotService._related_lessons(course_id, hits, db)
            result = {
                "answer": None,
                "grounded": False,
                "citations": [],
                "related_lessons": related,
                "thread_id": thread.id,
            }
            db.add(
                ChatMessage(
                    thread_id=thread.id,
                    role="assistant",
                    content="NOT_COVERED",
                    grounded=False,
                    citations=[],
                )
            )
            await db.commit()
            return result

        # Answer grounded in retrieved context.
        prompt = build_tutor_prompt(
            question,
            [h.text for h in course_hits],
            lesson_context,
            source_blocks=[h.text for h in source_hits],
            history=history,
        )
        completion = await gateway.generate(
            prompt, system=TUTOR_SYSTEM_PROMPT, max_tokens=600, temperature=0.0
        )
        answer_text = completion.text.strip()

        # Model may still decline if context is off-target.
        if answer_text.upper().startswith("NOT_COVERED"):
            related = await ChatbotService._related_lessons(course_id, hits, db)
            db.add(
                ChatMessage(thread_id=thread.id, role="assistant", content="NOT_COVERED",
                            grounded=False, citations=[])
            )
            await db.commit()
            return {
                "answer": None,
                "grounded": False,
                "citations": [],
                "related_lessons": related,
                "thread_id": thread.id,
            }

        citations = _dedupe_citations(hits)
        db.add(
            ChatMessage(
                thread_id=thread.id, role="assistant", content=answer_text,
                grounded=True, citations=citations,
            )
        )
        await db.commit()
        return {
            "answer": answer_text,
            "grounded": True,
            "citations": citations,
            "related_lessons": [],
            "thread_id": thread.id,
        }

    @staticmethod
    async def _history(thread_id: int, db: AsyncSession) -> list[tuple[str, str]]:
        """Last few exchanges of this thread, oldest first, as (role, content).

        Only the prompt sees this — the retrieval query is still the raw question.
        So a follow-up like "and its range?" now generates correctly against the
        context already retrieved, but does not itself retrieve better; that needs
        history-aware query rewriting, which costs an extra model call per turn.
        """
        if settings.CHAT_HISTORY_TURNS <= 0:
            return []
        limit = settings.CHAT_HISTORY_TURNS * 2  # a turn is user + assistant
        rows = (
            await db.execute(
                select(ChatMessage.role, ChatMessage.content)
                .where(ChatMessage.thread_id == thread_id)
                .order_by(ChatMessage.id.desc())
                .limit(limit)
            )
        ).all()
        cap = settings.CHAT_HISTORY_CHAR_CAP
        out = []
        for role, content in reversed(rows):  # back to chronological
            text = "(not covered by the material)" if content == "NOT_COVERED" else content
            if len(text) > cap:
                text = text[:cap] + "…"
            out.append((role, text))
        return out

    @staticmethod
    def _boost_current_lesson(hits, lesson_id: int | None, top_k: int):
        """Prefer chunks from the lesson the learner is on, without excluding others.

        The boost is applied to the SORT KEY only, never to ``hit.score`` — the
        abstain threshold must keep judging true similarity, or a nudged-but-
        irrelevant chunk could push a question over the line into a bad answer.
        """
        if lesson_id is None:
            return hits[:top_k]
        ranked = sorted(
            hits,
            key=lambda h: h.score + (settings.LESSON_BOOST if h.metadata.get("lesson_id") == lesson_id else 0.0),
            reverse=True,
        )
        return ranked[:top_k]

    @staticmethod
    def _retrieve(store, query_vec, course_id: int, source_top_k: int | None, lesson_id=None):
        """Retrieve reviewed course material and raw source material separately.

        One blended search would let the source document crowd out the lessons —
        it is roughly ten times larger, so it wins on volume alone. Querying the
        pools separately guarantees the admin-reviewed lessons always reach the
        prompt, with the original document appended as supporting detail for
        questions the generated lessons never covered.
        """
        # Over-fetch, then re-rank with the current-lesson boost and trim back to
        # top_k. Fetching only top_k would leave the boost nothing to promote.
        fetch_k = settings.RETRIEVAL_TOP_K * (
            settings.LESSON_CANDIDATE_MULTIPLIER if lesson_id is not None else 1
        )
        course_hits = ChatbotService._boost_current_lesson(
            store.search(
                query_vec,
                course_id=course_id,
                top_k=fetch_k,
                content_types=["lesson", "glossary"],
            ),
            lesson_id,
            settings.RETRIEVAL_TOP_K,
        )
        if not settings.INDEX_SOURCE_DOCUMENT:
            return course_hits, []
        k = source_top_k if source_top_k is not None else settings.SOURCE_RETRIEVAL_TOP_K
        if k <= 0:  # a 0 top_k means "no source pool"; Qdrant rejects limit=0 outright
            return course_hits, []
        source_hits = store.search(
            query_vec, course_id=course_id, top_k=k, content_types=["segment"]
        )
        return course_hits, source_hits

    @staticmethod
    async def _related_lessons(course_id: int, hits, db: AsyncSession) -> list[dict]:
        # Point the learner at lessons even when abstaining.
        lesson_ids = [h.metadata.get("lesson_id") for h in hits if h.metadata.get("lesson_id")]
        if not lesson_ids:
            from app.components.content.db_models import Module

            rows = (
                await db.execute(
                    select(Lesson.id, Lesson.title)
                    .join(Module, Module.id == Lesson.module_id)
                    .where(Module.course_id == course_id)
                    .limit(3)
                )
            ).all()
            return [{"lesson_id": r[0], "title": r[1]} for r in rows]
        out = []
        for lid in lesson_ids[:3]:
            lesson = await db.get(Lesson, lid)
            if lesson:
                out.append({"lesson_id": lesson.id, "title": lesson.title})
        return out

    @staticmethod
    async def explain_component(
        *,
        user_id: int,
        is_admin: bool,
        course_id: int,
        lesson_id: int | None,
        component: str,
        gateway: ModelGateway,
        db: AsyncSession,
    ) -> dict:
        # The 3D component explainer is just a scoped, grounded chat query — but it
        # pulls a deeper slice of the source document than ordinary chat, because
        # part specifics (dimensions, ratings, procedures) usually survive only in
        # the original manual, not in the summarised lesson body.
        question = f"Explain the component '{component}' and its function."
        return await ChatbotService.answer(
            user_id=user_id,
            is_admin=is_admin,
            course_id=course_id,
            lesson_id=lesson_id,
            question=question,
            thread_id=None,
            gateway=gateway,
            db=db,
            source_top_k=settings.COMPONENT_SOURCE_TOP_K,
        )
