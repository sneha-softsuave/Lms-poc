"""Chatbot API schemas (PRD 4.5 chat contract)."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    course_id: int
    lesson_id: int | None = None
    question: str
    thread_id: int | None = None


class RelatedLesson(BaseModel):
    lesson_id: int
    title: str


class ChatResponse(BaseModel):
    answer: str | None
    grounded: bool
    citations: list[dict] = []
    related_lessons: list[RelatedLesson] = []
    thread_id: int


class ExplainRequest(BaseModel):
    course_id: int
    lesson_id: int | None = None
    component: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list | None = None
    grounded: bool | None = None

    class Config:
        from_attributes = True
