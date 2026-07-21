"""Chatbot endpoints: sync (admin), chat, explain component, thread history."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.auth.db_models import ROLE_ADMIN, User
from app.components.chatbot.db_models import ChatMessage, ChatThread
from app.components.chatbot.models import (
    ChatRequest,
    ChatResponse,
    ExplainRequest,
    MessageOut,
)
from app.components.chatbot.service import ChatbotService
from app.components.chatbot.sync_service import SyncService
from app.core.auth import CurrentUser, require_admin
from app.database import get_db
from app.gateway import get_gateway
from app.gateway.base import ModelGateway

router = APIRouter(prefix="/api/v1", tags=["Chatbot"])

Db = Annotated[AsyncSession, Depends(get_db)]
Gateway = Annotated[ModelGateway, Depends(get_gateway)]


@router.post("/admin/chatbot/courses/{course_id}/sync")
async def sync_course(course_id: int, db: Db, gateway: Gateway, admin=Depends(require_admin())):
    """Index a course's lessons + glossary into the vector store (admin)."""
    return await SyncService.sync_course(course_id, gateway, db)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Db, user: CurrentUser, gateway: Gateway):
    result = await ChatbotService.answer(
        user_id=user.id,
        is_admin=user.role == ROLE_ADMIN,
        course_id=req.course_id,
        lesson_id=req.lesson_id,
        question=req.question,
        thread_id=req.thread_id,
        gateway=gateway,
        db=db,
    )
    from app.components.audit.service import AuditService

    await AuditService.record(
        db, actor_id=user.id, action="chat.answer",
        entity=f"course:{req.course_id}",
        detail={"grounded": result["grounded"], "thread_id": result["thread_id"]},
    )
    return result


@router.post("/chat/explain-component", response_model=ChatResponse)
async def explain_component(req: ExplainRequest, db: Db, user: CurrentUser, gateway: Gateway):
    return await ChatbotService.explain_component(
        user_id=user.id,
        is_admin=user.role == ROLE_ADMIN,
        course_id=req.course_id,
        lesson_id=req.lesson_id,
        component=req.component,
        gateway=gateway,
        db=db,
    )


@router.get("/chat/threads/{thread_id}", response_model=list[MessageOut])
async def thread_messages(thread_id: int, db: Db, user: CurrentUser):
    thread = await db.get(ChatThread, thread_id)
    if not thread or thread.user_id != user.id:
        raise HTTPException(404, "Thread not found")
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.thread_id == thread_id).order_by(ChatMessage.id)
    )
    return list(result.scalars().all())
