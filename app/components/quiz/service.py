"""Quiz taking + auto-grading (PRD 4.6, FR-5.6.3).

Only admin-approved questions are delivered. Objective questions (mcq/tf/short)
are auto-graded by normalized comparison. Scores are recorded as a QuizAttempt,
an audit event is written, and course progress is recomposed.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.audit.service import AuditService
from app.components.content.db_models import REVIEW_APPROVED, Module, Question, Quiz
from app.components.enrolment.service import EnrolmentService
from app.components.quiz.db_models import QuizAttempt

logger = logging.getLogger(__name__)


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _is_correct(question: Question, given: str) -> bool:
    g = _normalize(given)
    correct = _normalize(question.correct_answer)
    if question.qtype in ("mcq", "tf"):
        return g == correct
    # short answer: exact-normalized or substring either direction (lenient POC grading)
    return g == correct or (bool(g) and (g in correct or correct in g))


class QuizService:
    @staticmethod
    async def _approved_questions(module_id: int, db: AsyncSession) -> list[Question]:
        result = await db.execute(
            select(Question).where(
                Question.module_id == module_id, Question.review_status == REVIEW_APPROVED
            ).order_by(Question.id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_quiz(module_id: int, learner_id: int, is_admin: bool, db: AsyncSession) -> dict:
        module = await db.get(Module, module_id)
        if not module:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
        if not is_admin:
            enrolment = await EnrolmentService._get_enrolment(learner_id, module.course_id, db)
            if not enrolment:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Enrol in the course first")
        quiz = (
            await db.execute(select(Quiz).where(Quiz.module_id == module_id))
        ).scalar_one_or_none()
        questions = await QuizService._approved_questions(module_id, db)
        # Deliver WITHOUT the correct answer / rationale.
        return {
            "module_id": module_id,
            "title": quiz.title if quiz else f"{module.title} — Quiz",
            "pass_mark": quiz.pass_mark if quiz else 70,
            "questions": [
                {"id": q.id, "qtype": q.qtype, "stem": q.stem, "options": q.options,
                 "difficulty": q.difficulty}
                for q in questions
            ],
        }

    @staticmethod
    async def submit(
        module_id: int, learner_id: int, answers: dict, is_admin: bool, db: AsyncSession
    ) -> dict:
        module = await db.get(Module, module_id)
        if not module:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Module not found")
        if not is_admin:
            enrolment = await EnrolmentService._get_enrolment(learner_id, module.course_id, db)
            if not enrolment:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Enrol in the course first")

        questions = await QuizService._approved_questions(module_id, db)
        if not questions:
            raise HTTPException(status.HTTP_409_CONFLICT, "No approved questions to deliver")

        results, correct = [], 0
        # answers keyed by question id (str or int)
        norm_answers = {str(k): v for k, v in answers.items()}
        for q in questions:
            given = norm_answers.get(str(q.id), "")
            ok = _is_correct(q, given)
            correct += int(ok)
            results.append(
                {
                    "question_id": q.id,
                    "correct": ok,
                    "your_answer": given,
                    "correct_answer": q.correct_answer,
                    "rationale": q.rationale,
                    "source_ref": q.source_ref,
                }
            )

        total = len(questions)
        score_pct = int(round(100 * correct / total)) if total else 0
        quiz = (await db.execute(select(Quiz).where(Quiz.module_id == module_id))).scalar_one_or_none()
        pass_mark = quiz.pass_mark if quiz else 70
        passed = score_pct >= pass_mark

        attempt = QuizAttempt(
            learner_id=learner_id,
            module_id=module_id,
            course_id=module.course_id,
            score_pct=score_pct,
            correct=correct,
            total=total,
            passed=passed,
            answers=norm_answers,
        )
        db.add(attempt)
        await db.flush()
        await AuditService.record(
            db, actor_id=learner_id, action="quiz.submit",
            entity=f"module:{module_id}",
            detail={"score_pct": score_pct, "passed": passed, "attempt_id": attempt.id},
            commit=False,
        )
        await db.commit()

        # Quiz completion feeds progress recomputation (subject mastery derives from attempts).
        if not is_admin:
            await EnrolmentService.recompute(learner_id, module.course_id, db)

        return {
            "module_id": module_id,
            "score_pct": score_pct,
            "correct": correct,
            "total": total,
            "passed": passed,
            "pass_mark": pass_mark,
            "results": results,
        }
