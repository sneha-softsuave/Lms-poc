"""Canonical Defense LMS content hierarchy (PRD 4.1.2).

Subject -> Course -> Module -> Lesson, plus per-course Glossary and per-module
Question bank / Quiz. This clean schema replaces ThinkArguments' legacy
Pccore*/Term* tables. Every learning artifact carries a ``source_ref`` JSON
({doc, section, page}) for provenance and citations.

Generated content is a DRAFT: courses start ``status="draft"`` and questions
``review_status="pending"`` until an admin approves/publishes (PRD 4.1 rules).
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# course.status
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_UNPUBLISHED = "unpublished"

# question.review_status
REVIEW_PENDING = "pending"
REVIEW_APPROVED = "approved"
REVIEW_REJECTED = "rejected"


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    source_doc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    courses: Mapped[list["Course"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    objectives: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(24), default=STATUS_DRAFT, index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    subject: Mapped[Subject] = relationship(back_populates="courses")
    modules: Mapped[list["Module"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Module.order_index"
    )
    glossary: Mapped[list["GlossaryTerm"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped[Course] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order_index"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="module", cascade="all, delete-orphan"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    source_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {doc, section, page}
    model3d_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # attached 3D model

    module: Mapped[Module] = relationship(back_populates="lessons")


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    term: Mapped[str] = mapped_column(String(255))
    definition: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    course: Mapped[Course] = relationship(back_populates="glossary")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), index=True)
    qtype: Mapped[str] = mapped_column(String(16), default="mcq")  # mcq | tf | short
    stem: Mapped[str] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)  # for mcq/tf
    correct_answer: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="basic")  # basic|intermediate|advanced
    review_status: Mapped[str] = mapped_column(String(16), default=REVIEW_PENDING, index=True)
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    source_ref: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    module: Mapped[Module] = relationship(back_populates="questions")


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="Module Quiz")
    pass_mark: Mapped[int] = mapped_column(Integer, default=70)  # percent
