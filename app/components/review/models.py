"""Review workflow schemas."""

from pydantic import BaseModel


class QuestionEdit(BaseModel):
    stem: str | None = None
    options: list | None = None
    correct_answer: str | None = None
    rationale: str | None = None
    difficulty: str | None = None


class LessonEdit(BaseModel):
    title: str | None = None
    body: str | None = None
    model3d_id: str | None = None


class ReviewActionOut(BaseModel):
    id: int
    review_status: str

    class Config:
        from_attributes = True
