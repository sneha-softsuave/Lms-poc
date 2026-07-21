"""Enrolment + progress service (PRD 4.2, 4.3, 4.7).

Progress = completed lessons / total lessons. The resume point is the first
incomplete lesson in course order. Completing the last lesson marks the
enrolment complete (issues a completion record via status + completed_at).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.content.db_models import STATUS_PUBLISHED, Course, Lesson, Module
from app.components.enrolment.db_models import (
    ENROL_ACTIVE,
    ENROL_COMPLETED,
    Enrolment,
    LessonProgress,
)

logger = logging.getLogger(__name__)


async def _ordered_lessons(course_id: int, db: AsyncSession) -> list[Lesson]:
    result = await db.execute(
        select(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id)
        .order_by(Module.order_index, Lesson.order_index, Lesson.id)
    )
    return list(result.scalars().all())


async def _completed_lesson_ids(learner_id: int, course_id: int, db: AsyncSession) -> set[int]:
    result = await db.execute(
        select(LessonProgress.lesson_id).where(
            LessonProgress.learner_id == learner_id, LessonProgress.course_id == course_id
        )
    )
    return set(result.scalars().all())


class EnrolmentService:
    @staticmethod
    async def _get_enrolment(learner_id: int, course_id: int, db: AsyncSession) -> Enrolment | None:
        result = await db.execute(
            select(Enrolment).where(
                Enrolment.learner_id == learner_id, Enrolment.course_id == course_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def enrol(learner_id: int, course_id: int, db: AsyncSession) -> Enrolment:
        course = await db.get(Course, course_id)
        if not course or course.status != STATUS_PUBLISHED:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Published course not found")
        existing = await EnrolmentService._get_enrolment(learner_id, course_id, db)
        if existing:
            return existing
        lessons = await _ordered_lessons(course_id, db)
        enrolment = Enrolment(
            learner_id=learner_id,
            course_id=course_id,
            status=ENROL_ACTIVE,
            progress_pct=0,
            resume_lesson_id=lessons[0].id if lessons else None,
        )
        db.add(enrolment)
        await db.flush()
        from app.components.audit.service import AuditService

        await AuditService.record(
            db, actor_id=learner_id, action="enrolment.create",
            entity=f"course:{course_id}", commit=False,
        )
        await db.commit()
        await db.refresh(enrolment)
        return enrolment

    @staticmethod
    async def recompute(learner_id: int, course_id: int, db: AsyncSession) -> Enrolment:
        enrolment = await EnrolmentService._get_enrolment(learner_id, course_id, db)
        if not enrolment:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not enrolled")
        lessons = await _ordered_lessons(course_id, db)
        completed = await _completed_lesson_ids(learner_id, course_id, db)
        total = len(lessons)
        done = sum(1 for lesson in lessons if lesson.id in completed)
        enrolment.progress_pct = int(round(100 * done / total)) if total else 0
        resume = next((lesson.id for lesson in lessons if lesson.id not in completed), None)
        enrolment.resume_lesson_id = resume
        if total and done == total:
            newly_completed = enrolment.status != ENROL_COMPLETED
            enrolment.status = ENROL_COMPLETED
            enrolment.completed_at = enrolment.completed_at or datetime.now(UTC)
            if newly_completed:
                # Issue a completion certificate (FR-5.7.3).
                from app.components.certificates.service import CertificateService

                await CertificateService.issue(learner_id, course_id, db)
        else:
            enrolment.status = ENROL_ACTIVE
            enrolment.completed_at = None
        await db.commit()
        await db.refresh(enrolment)
        return enrolment

    @staticmethod
    async def add_time(learner_id: int, course_id: int, seconds: int, db: AsyncSession) -> Enrolment:
        """Accumulate time-on-task for an enrolment (FR-5.7.1)."""
        enrolment = await EnrolmentService._get_enrolment(learner_id, course_id, db)
        if not enrolment:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not enrolled")
        # Clamp per-call to guard against runaway values (max 1h per heartbeat).
        enrolment.time_spent_seconds += max(0, min(int(seconds), 3600))
        await db.commit()
        await db.refresh(enrolment)
        return enrolment

    @staticmethod
    async def complete_lesson(learner_id: int, lesson_id: int, db: AsyncSession) -> Enrolment:
        lesson = await db.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
        module = await db.get(Module, lesson.module_id)
        course_id = module.course_id
        enrolment = await EnrolmentService._get_enrolment(learner_id, course_id, db)
        if not enrolment:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Enrol in the course first")
        # upsert lesson progress (idempotent)
        already = await db.execute(
            select(LessonProgress).where(
                LessonProgress.learner_id == learner_id, LessonProgress.lesson_id == lesson_id
            )
        )
        if already.scalar_one_or_none() is None:
            db.add(LessonProgress(learner_id=learner_id, lesson_id=lesson_id, course_id=course_id))
            await db.commit()
        return await EnrolmentService.recompute(learner_id, course_id, db)

    @staticmethod
    async def list_for_learner(learner_id: int, db: AsyncSession) -> list[Enrolment]:
        result = await db.execute(
            select(Enrolment).where(Enrolment.learner_id == learner_id).order_by(Enrolment.id)
        )
        return list(result.scalars().all())
