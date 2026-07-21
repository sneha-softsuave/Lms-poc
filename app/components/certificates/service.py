"""Certificate issuance (PRD FR-5.7.3).

A certificate is issued once when a learner completes a course. The serial is
deterministic per (learner, course) so re-issue is idempotent.
"""

from __future__ import annotations

import hashlib
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.certificates.db_models import Certificate
from app.components.quiz.db_models import QuizAttempt

logger = logging.getLogger(__name__)


def _serial(learner_id: int, course_id: int) -> str:
    raw = f"CERT-{learner_id}-{course_id}"
    return "DLMS-" + hashlib.sha256(raw.encode()).hexdigest()[:10].upper()


class CertificateService:
    @staticmethod
    async def issue(learner_id: int, course_id: int, db: AsyncSession) -> Certificate:
        existing = (
            await db.execute(
                select(Certificate).where(
                    Certificate.learner_id == learner_id, Certificate.course_id == course_id
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        # Best quiz average across the course's attempts (0 if none taken).
        avg = (
            await db.execute(
                select(func.coalesce(func.avg(QuizAttempt.score_pct), 0)).where(
                    QuizAttempt.learner_id == learner_id, QuizAttempt.course_id == course_id
                )
            )
        ).scalar_one()
        cert = Certificate(
            serial=_serial(learner_id, course_id),
            learner_id=learner_id,
            course_id=course_id,
            score_pct=int(avg or 0),
        )
        db.add(cert)
        await db.flush()
        from app.components.audit.service import AuditService

        await AuditService.record(
            db, actor_id=learner_id, action="certificate.issue",
            entity=f"course:{course_id}", detail={"serial": cert.serial}, commit=False,
        )
        logger.info("Issued certificate %s (learner %d, course %d)", cert.serial, learner_id, course_id)
        return cert

    @staticmethod
    async def list_for_learner(learner_id: int, db: AsyncSession) -> list[Certificate]:
        result = await db.execute(
            select(Certificate).where(Certificate.learner_id == learner_id).order_by(Certificate.id.desc())
        )
        return list(result.scalars().all())
