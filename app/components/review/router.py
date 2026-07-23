"""Review & publish endpoints (admin-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.auth.db_models import User
from app.components.content.db_models import Module, Question
from app.components.content.models import CourseOut, CourseTree, QuestionOut
from app.components.content.service import load_course_tree, load_module_questions
from app.components.review.models import LessonEdit, QuestionEdit
from app.components.review.service import ReviewService
from app.core.auth import require_admin
from app.database import get_db
from app.gateway import get_gateway
from app.gateway.base import ModelGateway

router = APIRouter(prefix="/api/v1/review", tags=["Review"])

Db = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin())]
Gateway = Annotated[ModelGateway, Depends(get_gateway)]


@router.get("/drafts", response_model=list[CourseOut])
async def list_drafts(db: Db, admin: AdminUser):
    return await ReviewService.list_draft_courses(db)


@router.get("/courses", response_model=list[CourseOut])
async def list_courses(db: Db, admin: AdminUser, status: str | None = None):
    """All courses (optionally filtered by status) — lets admins reopen and edit
    published courses, e.g. to add/change 3D models after launch."""
    return await ReviewService.list_courses(db, status)


@router.get("/courses/{course_id}", response_model=CourseTree)
async def get_course(course_id: int, db: Db, admin: AdminUser):
    tree = await load_course_tree(course_id, db)
    if not tree:
        from fastapi import HTTPException

        raise HTTPException(404, "Course not found")
    return tree


@router.get("/modules/{module_id}/questions", response_model=list[QuestionOut])
async def module_questions(module_id: int, db: Db, admin: AdminUser):
    return await load_module_questions(module_id, db)


@router.get("/courses/{course_id}/questions", response_model=list[QuestionOut])
async def course_questions(course_id: int, db: Db, admin: AdminUser):
    result = await db.execute(
        select(Question)
        .join(Module, Module.id == Question.module_id)
        .where(Module.course_id == course_id)
        .order_by(Question.id)
    )
    return list(result.scalars().all())


@router.patch("/questions/{question_id}", response_model=QuestionOut)
async def edit_question(question_id: int, edit: QuestionEdit, db: Db, admin: AdminUser):
    return await ReviewService.edit_question(question_id, edit.model_dump(exclude_none=True), db)


@router.post("/questions/{question_id}/approve", response_model=QuestionOut)
async def approve_question(question_id: int, db: Db, admin: AdminUser):
    return await ReviewService.set_question_status(question_id, "approved", db)


@router.post("/questions/{question_id}/reject", response_model=QuestionOut)
async def reject_question(question_id: int, db: Db, admin: AdminUser):
    return await ReviewService.set_question_status(question_id, "rejected", db)


@router.patch("/lessons/{lesson_id}")
async def edit_lesson(lesson_id: int, edit: LessonEdit, db: Db, admin: AdminUser):
    lesson = await ReviewService.edit_lesson(lesson_id, edit.model_dump(exclude_none=True), db)
    return {"id": lesson.id, "title": lesson.title, "model3d_id": lesson.model3d_id}


@router.post("/courses/{course_id}/publish", response_model=CourseOut)
async def publish_course(course_id: int, db: Db, admin: AdminUser, gateway: Gateway):
    # Gateway is injected (not fetched inside the service) so publish-triggered
    # indexing honours dependency overrides in tests and smokes.
    return await ReviewService.publish_course(course_id, db, gateway)


@router.post("/courses/{course_id}/unpublish", response_model=CourseOut)
async def unpublish_course(course_id: int, db: Db, admin: AdminUser):
    return await ReviewService.unpublish_course(course_id, db)
