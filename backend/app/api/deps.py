"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Forbidden, Unauthorized
from app.db.models import User
from app.db.session import get_session
from app.services import auth as auth_service

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def current_user(request: Request, session: SessionDep) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise Unauthorized("You need to sign in to continue.", code="not_authenticated")
    user = await auth_service.authenticate(session, token)
    if user is None:
        raise Unauthorized("Your session has expired. Please sign in again.", code="session_expired")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def can_write(user: CurrentUser) -> User:
    """Mutations (upload, delete, create report) need the admin or analyst role; viewers are read-only."""
    if user.role not in ("admin", "analyst"):
        raise Forbidden("Your role doesn't allow changing data.", code="insufficient_role")
    return user


WriterUser = Annotated[User, Depends(can_write)]
