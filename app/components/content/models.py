"""Shared read schemas for the content hierarchy."""

from pydantic import BaseModel


class LessonOut(BaseModel):
    id: int
    title: str
    body: str
    order_index: int
    source_ref: dict | None = None
    model3d_id: str | None = None

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id: int
    qtype: str
    stem: str
    options: list | None = None
    correct_answer: str
    rationale: str
    difficulty: str
    review_status: str
    quality_score: int
    source_ref: dict | None = None

    class Config:
        from_attributes = True


class ModuleOut(BaseModel):
    id: int
    title: str
    order_index: int
    lessons: list[LessonOut] = []

    class Config:
        from_attributes = True


class GlossaryTermOut(BaseModel):
    id: int
    term: str
    definition: str
    source_ref: dict | None = None

    class Config:
        from_attributes = True


class CourseOut(BaseModel):
    id: int
    subject_id: int
    title: str
    description: str
    objectives: list
    version: int
    status: str

    class Config:
        from_attributes = True


class CourseTree(CourseOut):
    modules: list[ModuleOut] = []
    glossary: list[GlossaryTermOut] = []


class SubjectOut(BaseModel):
    id: int
    title: str
    description: str

    class Config:
        from_attributes = True
