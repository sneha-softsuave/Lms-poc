"""Auth service — register, authenticate, issue tokens, bootstrap admin."""

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.auth.db_models import ROLE_ADMIN, ROLE_LEARNER, User
from app.components.auth.models import RegisterRequest, TokenResponse
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)

logger = logging.getLogger(__name__)

VALID_ROLES = {ROLE_ADMIN, ROLE_LEARNER}


def _tokens_for(user: User) -> TokenResponse:
    claims = {"user_id": user.id, "email": user.email, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token({"user_id": user.id}),
    )


class AuthService:
    @staticmethod
    async def register(req: RegisterRequest, db: AsyncSession) -> User:
        if req.role not in VALID_ROLES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid role: {req.role}")
        existing = await db.execute(select(User).where(User.email == req.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        user = User(
            email=req.email,
            full_name=req.full_name,
            hashed_password=hash_password(req.password),
            role=req.role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(email: str, password: str, db: AsyncSession) -> TokenResponse:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
        return _tokens_for(user)

    @staticmethod
    async def refresh(refresh_token: str, db: AsyncSession) -> TokenResponse:
        payload = verify_refresh_token(refresh_token)
        if not payload or "user_id" not in payload:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
        user = await db.get(User, payload["user_id"])
        if not user or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
        return _tokens_for(user)

    @staticmethod
    async def bootstrap_admin(db: AsyncSession) -> None:
        """Create the default admin on first startup if no admin exists."""
        result = await db.execute(select(User).where(User.role == ROLE_ADMIN))
        if result.first() is not None:
            return
        admin = User(
            email=settings.BOOTSTRAP_ADMIN_EMAIL,
            full_name="Bootstrap Admin",
            hashed_password=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
            role=ROLE_ADMIN,
        )
        db.add(admin)
        await db.commit()
        logger.info("Bootstrap admin created: %s", settings.BOOTSTRAP_ADMIN_EMAIL)
