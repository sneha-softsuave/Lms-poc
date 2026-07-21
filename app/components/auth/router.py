"""Auth endpoints: register, login, refresh, me."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.auth.models import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.components.auth.service import AuthService
from app.core.auth import CurrentUser, require_admin
from app.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=UserOut, status_code=201)
async def register(req: RegisterRequest, db: Db):
    """Self-register (defaults to learner). Creating admins is gated below."""
    # Force self-registration to learner; admins are created via /admin/users.
    req.role = "learner"
    return await AuthService.register(req, db)


@router.post("/admin/users", response_model=UserOut, status_code=201)
async def admin_create_user(
    req: RegisterRequest, db: Db, _admin=Depends(require_admin())
):
    """Admin-only: create a user with any role (admin or learner)."""
    return await AuthService.register(req, db)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Db):
    return await AuthService.authenticate(req.email, req.password, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: Db):
    return await AuthService.refresh(req.refresh_token, db)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
