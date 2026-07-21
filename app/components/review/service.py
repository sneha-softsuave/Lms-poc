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
    async def publish_course(course_id: int, db: AsyncSession) -> Course:
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
        return course

    @staticmethod
    async def unpublish_course(course_id: int, db: AsyncSession) -> Course:
        course = await db.get(Course, course_id)
        if not course:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
        course.status = STATUS_UNPUBLISHED
        await db.commit()
        await db.refresh(course)
        return course

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
