"""Audit service — append-only writer + admin reader."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.audit.db_models import AuditEvent


class AuditService:
    @staticmethod
    async def record(
        db: AsyncSession,
        *,
        actor_id: int | None,
        action: str,
        entity: str = "",
        detail: dict | None = None,
        commit: bool = True,
    ) -> None:
        """Append one immutable event. ``commit=False`` to flush within a caller's txn."""
        db.add(AuditEvent(actor_id=actor_id, action=action, entity=entity, detail=detail))
        if commit:
            await db.commit()

    @staticmethod
    async def list_events(
        db: AsyncSession, *, action: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        stmt = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
        if action:
            stmt = stmt.where(AuditEvent.action == action)
        result = await db.execute(stmt)
        return list(result.scalars().all())
