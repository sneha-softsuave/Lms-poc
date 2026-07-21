"""Immutable audit log (PRD 4.10, FR-5.7.5).

Append-only: rows are only ever inserted (no update/delete paths in the service).
Records chatbot interactions, quiz attempts, enrolments, publishes and admin
actions.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)  # e.g. chat.answer, quiz.submit
    entity: Mapped[str] = mapped_column(String(64), default="")   # e.g. course:1, quiz:3
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)
