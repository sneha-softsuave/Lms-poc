"""3D model endpoints (PRD 4.4): browse library, associate to lesson, viewer data."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.components.content.db_models import Lesson, Module
from app.components.enrolment.service import EnrolmentService
from app.components.models3d.db_models import Model3D
from app.components.models3d.models import (
    AssociateRequest,
    Model3DDetail,
    Model3DOut,
    ViewerPayload,
)
from app.core.auth import CurrentUser, require_admin
from app.database import get_db

router = APIRouter(prefix="/api/v1/models3d", tags=["3D Models"])

Db = Annotated[AsyncSession, Depends(get_db)]


async def _get_model(db: AsyncSession, model_key: str) -> Model3D | None:
    result = await db.execute(
        select(Model3D).where(Model3D.model_key == model_key).options(selectinload(Model3D.hotspots))
    )
    return result.scalar_one_or_none()


@router.get("", response_model=list[Model3DOut])
async def list_models(db: Db, user: CurrentUser):
    return list((await db.execute(select(Model3D).order_by(Model3D.id))).scalars().all())


@router.get("/{model_key}", response_model=Model3DDetail)
async def get_model(model_key: str, db: Db, user: CurrentUser):
    model = await _get_model(db, model_key)
    if not model:
        raise HTTPException(404, "Model not found")
    return model


@router.post("/lessons/{lesson_id}/associate")
async def associate_model(lesson_id: int, req: AssociateRequest, db: Db, admin=Depends(require_admin())):
    """Admin attaches (or, with an empty key, detaches) a preloaded model on a
    lesson (FR-5.1.4). Allowed at any time — including on published courses, so
    the 3D library can be curated after launch. 3D association does not change
    lesson text, so no chatbot re-index is required."""
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    if req.model_key:
        model = await _get_model(db, req.model_key)
        if not model:
            raise HTTPException(404, f"Unknown model_key: {req.model_key}")
        lesson.model3d_id = req.model_key
    else:
        lesson.model3d_id = None  # detach
    from app.components.audit.service import AuditService

    await AuditService.record(
        db, actor_id=admin.id, action="model3d.associate",
        entity=f"lesson:{lesson_id}", detail={"model_key": req.model_key or None}, commit=False,
    )
    await db.commit()
    return {"lesson_id": lesson_id, "model3d_id": lesson.model3d_id}


@router.get("/lessons/{lesson_id}/viewer", response_model=ViewerPayload)
async def lesson_viewer(lesson_id: int, db: Db, user: CurrentUser):
    """Viewer payload for the React 3D component: glb + hotspots."""
    lesson = await db.get(Lesson, lesson_id)
    if not lesson or not lesson.model3d_id:
        raise HTTPException(404, "No 3D model associated with this lesson")
    module = await db.get(Module, lesson.module_id)
    if user.role != "admin":
        enrolment = await EnrolmentService._get_enrolment(user.id, module.course_id, db)
        if not enrolment:
            raise HTTPException(403, "Enrol in the course to view the 3D model")
    model = await _get_model(db, lesson.model3d_id)
    if not model:
        raise HTTPException(404, "Associated model missing from library")
    return ViewerPayload(
        lesson_id=lesson_id,
        model_key=model.model_key,
        name=model.name,
        glb_uri=model.glb_uri,
        hotspots=model.hotspots,
    )
