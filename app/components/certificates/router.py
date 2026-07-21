"""Certificate endpoints (PRD FR-5.7.3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.certificates.db_models import Certificate
from app.components.certificates.service import CertificateService
from app.components.content.db_models import Course, Subject
from app.core.auth import CurrentUser
from app.database import get_db

router = APIRouter(prefix="/api/v1/certificates", tags=["Certificates"])

Db = Annotated[AsyncSession, Depends(get_db)]


class CertificateOut(BaseModel):
    serial: str
    course_id: int
    course_title: str
    subject_title: str
    learner_name: str
    score_pct: int
    issued_at: str


async def _to_out(cert: Certificate, learner_name: str, db: AsyncSession) -> CertificateOut:
    course = await db.get(Course, cert.course_id)
    subject = await db.get(Subject, course.subject_id) if course else None
    return CertificateOut(
        serial=cert.serial,
        course_id=cert.course_id,
        course_title=course.title if course else "",
        subject_title=subject.title if subject else "",
        learner_name=learner_name,
        score_pct=cert.score_pct,
        issued_at=cert.issued_at.isoformat(),
    )


@router.get("/me", response_model=list[CertificateOut])
async def my_certificates(db: Db, user: CurrentUser):
    certs = await CertificateService.list_for_learner(user.id, db)
    return [await _to_out(c, user.full_name or user.email, db) for c in certs]


@router.get("/{serial}", response_model=CertificateOut)
async def get_certificate(serial: str, db: Db, user: CurrentUser):
    from sqlalchemy import select

    cert = (await db.execute(select(Certificate).where(Certificate.serial == serial))).scalar_one_or_none()
    if not cert or (cert.learner_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Certificate not found")
    return await _to_out(cert, user.full_name or user.email, db)
