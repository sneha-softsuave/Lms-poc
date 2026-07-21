"""Shared content-loading helpers (used by generation, review, catalog, quiz)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.components.content.db_models import Course, Module, Question


async def load_course_tree(course_id: int, db: AsyncSession) -> Course | None:
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons),
            selectinload(Course.glossary),
        )
    )
    return result.scalar_one_or_none()


async def load_module_questions(
    module_id: int, db: AsyncSession, *, only_approved: bool = False
) -> list[Question]:
    stmt = select(Question).where(Question.module_id == module_id)
    if only_approved:
        from app.components.content.db_models import REVIEW_APPROVED

        stmt = stmt.where(Question.review_status == REVIEW_APPROVED)
    result = await db.execute(stmt.order_by(Question.id))
    return list(result.scalars().all())
