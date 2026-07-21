"""Grounded doubt-clearing chatbot (PRD 4.5) + component explainer (4.4.2).

Flow: embed query (gateway) -> access-filtered retrieval (course_id) -> if top
score < ABSTAIN_THRESHOLD, abstain (grounded=false, answer=null, related
lessons); else answer from retrieved context via the gateway, with citations
drawn from the chunks' source_refs. Multi-turn: messages persist per thread and
the current lesson is passed as context.
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
    ) -> dict:
        # Access control: learner must be enrolled (admins exempt).
        if not is_admin:
            enrolment = await EnrolmentService._get_enrolment(user_id, course_id, db)
            if not enrolment:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Enrol in the course to ask questions")

        thread = await ChatbotService._resolve_thread(user_id, course_id, thread_id, db)
        db.add(ChatMessage(thread_id=thread.id, role="user", content=question))

        # Retrieve (access-filtered by course_id BEFORE ranking).
        store = get_vector_store()
        query_vec = (await gateway.embed([question]))[0]
        hits = store.search(query_vec, course_id=course_id, top_k=settings.RETRIEVAL_TOP_K)
        top_score = hits[0].score if hits else 0.0

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
        context_blocks = [h.text for h in hits]
        prompt = build_tutor_prompt(question, context_blocks, lesson_context)
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
        # The 3D component explainer is just a scoped, grounded chat query.
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
        )
