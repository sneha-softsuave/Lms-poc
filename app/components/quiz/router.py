"""Quiz taking endpoints (learner)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.quiz.service import QuizService
from app.core.auth import CurrentUser
from app.database import get_db

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz"])

Db = Annotated[AsyncSession, Depends(get_db)]


class SubmitRequest(BaseModel):
    answers: dict  # {question_id: answer}


@router.get("/modules/{module_id}")
async def get_quiz(module_id: int, db: Db, user: CurrentUser):
    return await QuizService.get_quiz(module_id, user.id, user.role == "admin", db)


@router.post("/modules/{module_id}/submit")
async def submit_quiz(module_id: int, req: SubmitRequest, db: Db, user: CurrentUser):
    return await QuizService.submit(module_id, user.id, req.answers, user.role == "admin", db)
