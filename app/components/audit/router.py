"""Audit endpoints (admin-only, read)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.audit.service import AuditService
from app.core.auth import require_admin
from app.database import get_db

router = APIRouter(prefix="/api/v1/admin/audit", tags=["Audit"])

Db = Annotated[AsyncSession, Depends(get_db)]


class AuditOut(BaseModel):
    id: int
    actor_id: int | None
    action: str
    entity: str
    detail: dict | None = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[AuditOut])
async def list_audit(db: Db, admin=Depends(require_admin()), action: str | None = None, limit: int = 100):
    return await AuditService.list_events(db, action=action, limit=limit)
