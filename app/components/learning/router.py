"""Learning delivery (PRD 4.3): guided lesson flow, completion, resume.

A learner must be enrolled to view a lesson. Completing a lesson advances
progress and moves the resume point; the response echoes updated progress so a
thin UI needs a single round-trip.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.content.db_models import Lesson, Module
from app.components.content.models import LessonOut
from app.components.enrolment.models import EnrolmentOut
from app.components.enrolment.service import EnrolmentService
from app.core.auth import CurrentUser
from app.database import get_db


class HeartbeatRequest(BaseModel):
    seconds: int

router = APIRouter(prefix="/api/v1/learning", tags=["Learning"])

Db = Annotated[AsyncSession, Depends(get_db)]


class LessonView(BaseModel):
    lesson: LessonOut
    course_id: int
    has_3d: bool


async def _course_id_for_lesson(lesson: Lesson, db: AsyncSession) -> int:
    module = await db.get(Module, lesson.module_id)
    return module.course_id


@router.get("/lessons/{lesson_id}", response_model=LessonView)
async def get_lesson(lesson_id: int, db: Db, user: CurrentUser):
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    course_id = await _course_id_for_lesson(lesson, db)
    enrolment = await EnrolmentService._get_enrolment(user.id, course_id, db)
    if not enrolment and user.role != "admin":
        raise HTTPException(403, "Enrol in the course to view this lesson")
    return LessonView(
        lesson=LessonOut.model_validate(lesson),
        course_id=course_id,
        has_3d=lesson.model3d_id is not None,
    )


@router.post("/lessons/{lesson_id}/complete", response_model=EnrolmentOut)
async def complete_lesson(lesson_id: int, db: Db, user: CurrentUser):
    return await EnrolmentService.complete_lesson(user.id, lesson_id, db)


@router.post("/courses/{course_id}/heartbeat", response_model=EnrolmentOut)
async def heartbeat(course_id: int, req: HeartbeatRequest, db: Db, user: CurrentUser):
    """Accumulate time-on-task while a learner studies (FR-5.7.1)."""
    return await EnrolmentService.add_time(user.id, course_id, req.seconds, db)


@router.get("/courses/{course_id}/resume", response_model=EnrolmentOut)
async def resume_point(course_id: int, db: Db, user: CurrentUser):
    enrolment = await EnrolmentService._get_enrolment(user.id, course_id, db)
    if not enrolment:
        raise HTTPException(404, "Not enrolled")
    return enrolment
