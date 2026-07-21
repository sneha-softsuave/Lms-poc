"""Enrolment endpoints: self-enrol, admin assign, learner dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.auth.db_models import User
from app.components.content.db_models import Course, Subject
from app.components.enrolment.models import AssignRequest, DashboardCourse, EnrolmentOut
from app.components.enrolment.service import EnrolmentService
from app.core.auth import CurrentUser, require_admin, require_learner
from app.database import get_db

router = APIRouter(prefix="/api/v1/enrolments", tags=["Enrolment"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("/courses/{course_id}", response_model=EnrolmentOut, status_code=201)
async def self_enrol(course_id: int, db: Db, user=Depends(require_learner())):
    return await EnrolmentService.enrol(user.id, course_id, db)


@router.post("/assign", response_model=EnrolmentOut, status_code=201)
async def admin_assign(req: AssignRequest, db: Db, admin=Depends(require_admin())):
    return await EnrolmentService.enrol(req.learner_id, req.course_id, db)


@router.get("/me", response_model=list[DashboardCourse])
async def my_dashboard(db: Db, user: CurrentUser):
    enrolments = await EnrolmentService.list_for_learner(user.id, db)
    out: list[DashboardCourse] = []
    for e in enrolments:
        course = await db.get(Course, e.course_id)
        subject = await db.get(Subject, course.subject_id) if course else None
        out.append(
            DashboardCourse(
                course_id=e.course_id,
                course_title=course.title if course else "",
                subject_title=subject.title if subject else "",
                status=e.status,
                progress_pct=e.progress_pct,
                time_spent_seconds=e.time_spent_seconds,
                resume_lesson_id=e.resume_lesson_id,
            )
        )
    return out
