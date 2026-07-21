"""Ingestion endpoints (admin-only): upload material, list, inspect segments."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.components.auth.db_models import User
from app.components.ingestion.db_models import Document
from app.components.ingestion.models import DocumentDetail, DocumentOut
from app.components.ingestion.service import IngestionService
from app.core.auth import require_admin
from app.core.config import settings
from app.database import get_db
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/ingestion", tags=["Ingestion"])

Db = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin())]


@router.post("/upload", response_model=DocumentDetail, status_code=201)
async def upload(db: Db, admin: AdminUser, file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > settings.CONTENT_EXTRACTION_MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")
    try:
        doc = await IngestionService.ingest(
            data=data,
            filename=file.filename or "upload",
            content_type=file.content_type,
            uploaded_by=admin.id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc
    # reload with segments for the response
    result = await db.execute(
        select(Document).where(Document.id == doc.id).options(selectinload(Document.segments))
    )
    return result.scalar_one()


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: Db, admin: AdminUser):
    return await IngestionService.list_all(db)


@router.get("/{doc_id}", response_model=DocumentDetail)
async def get_document(doc_id: int, db: Db, admin: AdminUser):
    result = await db.execute(
        select(Document).where(Document.id == doc_id).options(selectinload(Document.segments))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc
