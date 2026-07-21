"""Enrolment API schemas."""

from datetime import datetime

from pydantic import BaseModel


class EnrolmentOut(BaseModel):
    id: int
    learner_id: int
    course_id: int
    status: str
    progress_pct: int
    time_spent_seconds: int = 0
    resume_lesson_id: int | None = None
    enrolled_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class AssignRequest(BaseModel):
    learner_id: int
    course_id: int


class DashboardCourse(BaseModel):
    course_id: int
    course_title: str
    subject_title: str
    status: str
    progress_pct: int
    time_spent_seconds: int = 0
    resume_lesson_id: int | None = None
