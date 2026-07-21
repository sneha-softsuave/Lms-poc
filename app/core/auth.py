"""Authentication + RBAC dependencies.

``get_current_user`` resolves the Bearer token to a User row; ``require_role``
and the ``require_admin`` / ``require_learner`` helpers enforce the two POC
roles per-route (PRD FR-5.1.6).
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.components.auth.db_models import ROLE_ADMIN, ROLE_LEARNER, User
from app.core.security import verify_token
from app.database import get_db

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = verify_token(credentials.credentials)
    if not payload or "user_id" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = await db.get(User, payload["user_id"])
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    async def _dep(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requires role: {' or '.join(roles)}",
            )
        return user

    return _dep


def require_admin():
    return require_role(ROLE_ADMIN)


def require_learner():
    # Admins can do anything a learner can.
    return require_role(ROLE_LEARNER, ROLE_ADMIN)


async def _lookup_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
