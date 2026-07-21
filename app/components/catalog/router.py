"""Course catalog (PRD 4.2): published courses grouped by subject.

Read-only browsing for any authenticated user. Only PUBLISHED courses appear.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.content.db_models import STATUS_PUBLISHED, Course, Subject
from app.components.content.models import CourseOut, CourseTree
from app.components.content.service import load_course_tree
from app.core.auth import CurrentUser
from app.database import get_db

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])

Db = Annotated[AsyncSession, Depends(get_db)]


class SubjectGroup(BaseModel):
    subject_id: int
    subject_title: str
    courses: list[CourseOut]


@router.get("/subjects", response_model=list[SubjectGroup])
async def catalog_by_subject(db: Db, user: CurrentUser):
    result = await db.execute(
        select(Course).where(Course.status == STATUS_PUBLISHED).order_by(Course.subject_id)
    )
    courses = list(result.scalars().all())
    groups: dict[int, SubjectGroup] = {}
    for course in courses:
        if course.subject_id not in groups:
            subject = await db.get(Subject, course.subject_id)
            groups[course.subject_id] = SubjectGroup(
                subject_id=course.subject_id,
                subject_title=subject.title if subject else "",
                courses=[],
            )
        groups[course.subject_id].courses.append(CourseOut.model_validate(course))
    return list(groups.values())


@router.get("/courses/{course_id}", response_model=CourseTree)
async def course_detail(course_id: int, db: Db, user: CurrentUser):
    course = await load_course_tree(course_id, db)
    if not course or course.status != STATUS_PUBLISHED:
        raise HTTPException(404, "Published course not found")
    return course
