"""Admin analytics (PRD 4.7, FR-5.7.4): cohort progress across courses/subjects,
subject mastery, and the weakest topics (modules with the lowest quiz scores).
"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.content.db_models import Course, Module, Subject
from app.components.enrolment.db_models import Enrolment
from app.components.quiz.db_models import QuizAttempt


class AnalyticsService:
    @staticmethod
    async def cohort_progress(db: AsyncSession) -> list[dict]:
        """Average progress % and enrolment counts per published course."""
        rows = (
            await db.execute(
                select(
                    Course.id,
                    Course.title,
                    Subject.title,
                    func.count(Enrolment.id),
                    func.coalesce(func.avg(Enrolment.progress_pct), 0),
                    func.sum(case((Enrolment.status == "completed", 1), else_=0)),
                )
                .join(Subject, Subject.id == Course.subject_id)
                .join(Enrolment, Enrolment.course_id == Course.id, isouter=True)
                .group_by(Course.id, Course.title, Subject.title)
                .order_by(Course.id)
            )
        ).all()
        return [
            {
                "course_id": r[0],
                "course_title": r[1],
                "subject_title": r[2],
                "enrolled": r[3],
                "avg_progress_pct": round(float(r[4]), 1),
                "completed": int(r[5] or 0),
            }
            for r in rows
        ]

    @staticmethod
    async def subject_mastery(db: AsyncSession) -> list[dict]:
        """Average quiz score per subject (mastery signal)."""
        rows = (
            await db.execute(
                select(Subject.title, func.avg(QuizAttempt.score_pct), func.count(QuizAttempt.id))
                .join(Course, Course.subject_id == Subject.id)
                .join(QuizAttempt, QuizAttempt.course_id == Course.id)
                .group_by(Subject.title)
                .order_by(func.avg(QuizAttempt.score_pct))
            )
        ).all()
        return [
            {"subject_title": r[0], "avg_score_pct": round(float(r[1]), 1), "attempts": r[2]}
            for r in rows
        ]

    @staticmethod
    async def weakest_topics(db: AsyncSession, limit: int = 5) -> list[dict]:
        """Modules with the lowest average quiz score (weakest topics)."""
        rows = (
            await db.execute(
                select(
                    Module.id,
                    Module.title,
                    Course.title,
                    func.avg(QuizAttempt.score_pct),
                    func.count(QuizAttempt.id),
                )
                .join(Course, Course.id == Module.course_id)
                .join(QuizAttempt, QuizAttempt.module_id == Module.id)
                .group_by(Module.id, Module.title, Course.title)
                .order_by(func.avg(QuizAttempt.score_pct))
                .limit(limit)
            )
        ).all()
        return [
            {
                "module_id": r[0],
                "module_title": r[1],
                "course_title": r[2],
                "avg_score_pct": round(float(r[3]), 1),
                "attempts": r[4],
            }
            for r in rows
        ]
