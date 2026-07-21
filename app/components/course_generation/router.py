"""Course generation endpoints (admin-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.auth.db_models import User
from app.components.content.models import CourseTree
from app.components.content.service import load_course_tree
from app.components.course_generation.service import CourseGenerationService
from app.core.auth import require_admin
from app.database import get_db
from app.gateway import get_gateway
from app.gateway.base import ModelGateway

router = APIRouter(prefix="/api/v1/course-generation", tags=["Course Generation"])

Db = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin())]
Gateway = Annotated[ModelGateway, Depends(get_gateway)]


@router.post("/documents/{doc_id}/generate", response_model=CourseTree, status_code=201)
async def generate_course(doc_id: int, db: Db, admin: AdminUser, gateway: Gateway):
    """Run the AI structuring pipeline on an ingested document -> draft course."""
    try:
        course = await CourseGenerationService.generate_from_document(doc_id, gateway, db)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    tree = await load_course_tree(course.id, db)
    return tree
