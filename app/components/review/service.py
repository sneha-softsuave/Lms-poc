"""Review & publish workflow (PRD 4.1 rules, FR-5.2.5).

Drafts -> admin edits/approves/rejects questions and edits lessons -> publishes
the course. Publishing requires every question in the course to be resolved
(approved or rejected), never left pending. Publishing bumps the version.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.content.db_models import (
    REVIEW_APPROVED,
    REVIEW_PENDING,
    REVIEW_REJECTED,
    STATUS_PUBLISHED,
    STATUS_UNPUBLISHED,
    Course,
    Lesson,
    Module,
    Question,
)

logger = logging.getLogger(__name__)


class ReviewService:
    @staticmethod
    async def set_question_status(question_id: int, new_status: str, db: AsyncSession) -> Question:
        if new_status not in (REVIEW_APPROVED, REVIEW_REJECTED, REVIEW_PENDING):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid status: {new_status}")
        q = await db.get(Question, question_id)
        if not q:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
        q.review_status = new_status
        await db.commit()
        await db.refresh(q)
        return q

    @staticmethod
    async def edit_question(question_id: int, fields: dict, db: AsyncSession) -> Question:
        q = await db.get(Question, question_id)
        if not q:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
        for k, v in fields.items():
            if v is not None:
                setattr(q, k, v)
        await db.commit()
        await db.refresh(q)
        return q

    @staticmethod
    async def edit_lesson(lesson_id: int, fields: dict, db: AsyncSession) -> Lesson:
        lesson = await db.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
        for k, v in fields.items():
            if v is not None:
                setattr(lesson, k, v)
        await db.commit()
        await db.refresh(lesson)
        return lesson

    @staticmethod
    async def publish_course(course_id: int, db: AsyncSession, gateway=None) -> Course:
        course = await db.get(Course, course_id)
        if not course:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")

        # No question may remain pending in a published course.
        pending = await db.execute(
            select(Question.id)
            .join(Module, Module.id == Question.module_id)
            .where(Module.course_id == course_id, Question.review_status == REVIEW_PENDING)
        )
        if pending.first() is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Cannot publish: some questions are still pending review. "
                "Approve or reject every question first.",
            )

        if course.status == STATUS_PUBLISHED:
            return course
        course.status = STATUS_PUBLISHED
        course.version += 1
        from app.components.audit.service import AuditService

        await AuditService.record(
            db, actor_id=None, action="course.publish",
            entity=f"course:{course_id}", detail={"version": course.version}, commit=False,
        )
        await db.commit()
        await db.refresh(course)
        logger.info("Published course %s (v%d)", course.title, course.version)
        await ReviewService._index_for_chatbot(course_id, db, gateway)
        return course

    @staticmethod
    async def _index_for_chatbot(course_id: int, db: AsyncSession, gateway=None) -> None:
        """Index the freshly published course so the chatbot can answer on it.

        Deliberately non-fatal: publishing is the compliance-gated action and must
        not be undone by an embedding provider being unreachable. A failure here
        leaves the course published but unsearchable until an admin re-runs
        POST /api/v1/admin/chatbot/courses/{id}/sync.
        """
        try:
            from app.components.chatbot.sync_service import SyncService

            if gateway is None:  # non-request callers (scripts, startup)
                from app.gateway import get_gateway

                gateway = get_gateway()
            stats = await SyncService.sync_course(course_id, gateway, db)
            logger.info("Chatbot index updated for course %d: %s", course_id, stats)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Chatbot indexing failed for course %d (%s): %s — course is published "
                "but not yet searchable; re-run the admin sync endpoint.",
                course_id, type(exc).__name__, exc,
            )

    @staticmethod
    async def unpublish_course(course_id: int, db: AsyncSession) -> Course:
        course = await db.get(Course, course_id)
        if not course:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
        course.status = STATUS_UNPUBLISHED
        await db.commit()
        await db.refresh(course)
        logger.info("Unpublished course %s", course.title)
        await ReviewService._purge_from_chatbot(course_id, db)
        return course

    @staticmethod
    async def _purge_from_chatbot(course_id: int, db: AsyncSession) -> None:
        """Drop the course's vectors so the chatbot stops answering from it.

        Withdrawing a course from the catalog must never be blocked by the vector
        store being down, so this is non-fatal like the publish-side sync — but it
        logs at ERROR, not WARNING: a failure here leaves withdrawn content still
        answerable over /api/v1/chat to enrolled learners, which is a compliance
        exposure rather than a missing feature.
        """
        try:
            from app.components.chatbot.sync_service import SyncService

            stats = await SyncService.purge_course(course_id, db)
            logger.info("Chatbot index purged for course %d: %s", course_id, stats)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Chatbot index purge FAILED for course %d (%s): %s - the course is "
                "unpublished but its content may still be answerable in chat; "
                "re-run unpublish once the vector store is reachable.",
                course_id, type(exc).__name__, exc,
            )

    @staticmethod
    async def list_draft_courses(db: AsyncSession) -> list[Course]:
        from app.components.content.db_models import STATUS_DRAFT

        result = await db.execute(select(Course).where(Course.status == STATUS_DRAFT))
        return list(result.scalars().all())

    @staticmethod
    async def list_courses(db: AsyncSession, status: str | None = None) -> list[Course]:
        stmt = select(Course).order_by(Course.id.desc())
        if status:
            stmt = stmt.where(Course.status == status)
        result = await db.execute(stmt)
        return list(result.scalars().all())
