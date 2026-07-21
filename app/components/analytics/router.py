"""Admin analytics endpoints (PRD 4.7)."""

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.analytics.service import AnalyticsService
from app.components.auth.db_models import User
from app.components.content.db_models import Course
from app.components.enrolment.db_models import Enrolment
from app.core.auth import require_admin
from app.database import get_db

router = APIRouter(prefix="/api/v1/admin/analytics", tags=["Analytics"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/cohort-progress")
async def cohort_progress(db: Db, admin=Depends(require_admin())):
    return await AnalyticsService.cohort_progress(db)


@router.get("/subject-mastery")
async def subject_mastery(db: Db, admin=Depends(require_admin())):
    return await AnalyticsService.subject_mastery(db)


@router.get("/weakest-topics")
async def weakest_topics(db: Db, admin=Depends(require_admin()), limit: int = 5):
    return await AnalyticsService.weakest_topics(db, limit)


@router.get("/export.csv")
async def export_results(db: Db, admin=Depends(require_admin())):
    """Export per-learner enrolment results as CSV (FR-5.7.4)."""
    rows = (
        await db.execute(
            select(
                User.email, User.full_name, Course.title,
                Enrolment.status, Enrolment.progress_pct,
                Enrolment.time_spent_seconds, Enrolment.completed_at,
            )
            .join(User, User.id == Enrolment.learner_id)
            .join(Course, Course.id == Enrolment.course_id)
            .order_by(Course.title, User.email)
        )
    ).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["learner_email", "learner_name", "course", "status",
                     "progress_pct", "time_minutes", "completed_at"])
    for r in rows:
        writer.writerow([r[0], r[1], r[2], r[3], r[4], round((r[5] or 0) / 60, 1),
                         r[6].isoformat() if r[6] else ""])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=learning_results.csv"},
    )
