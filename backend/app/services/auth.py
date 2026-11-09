"""Registration, login, logout and session lookup."""

import asyncio
import uuid
from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Conflict, TooManyRequests, Unauthorized
from app.core.security import dummy_hash, hash_password, hash_token, new_session_token, verify_password
from app.db.base import utcnow
from app.db.models import AuthSession, User
from app.schemas.auth import LoginIn, RegisterIn, UserOut

#: A session's expiry slides forward, but is only written back this often (not on every request).
_TOUCH_INTERVAL = timedelta(minutes=5)


def to_user_out(user: User) -> UserOut:
    return UserOut(id=str(user.id), name=user.name, email=user.email, role=user.role)


async def register(
    session: AsyncSession, data: RegisterIn, *, user_agent: str | None, ip: str | None
) -> tuple[User, str]:
    if await session.scalar(select(User.id).where(User.email == data.email)):
        raise Conflict("An account with this email already exists. Try signing in instead.", code="email_taken")
    # Argon2 is deliberately slow (~0.2 s of CPU): keep it off the event loop.
    password_hash = await asyncio.to_thread(hash_password, data.password)
    # Each registration owns an isolated workspace (all data is scoped to its owner), hence "admin".
    user = User(email=data.email, name=data.name, password_hash=password_hash, role="admin")
    session.add(user)
    try:
        await session.flush()
    except IntegrityError:  # lost a race with a concurrent registration of the same e-mail
        await session.rollback()
        raise Conflict(
            "An account with this email already exists. Try signing in instead.", code="email_taken"
        ) from None
    token = await _open_session(session, user.id, user_agent, ip)
    await session.commit()
    return user, token


async def login(session: AsyncSession, data: LoginIn, *, user_agent: str | None, ip: str | None) -> tuple[User, str]:
    settings = get_settings()
    now = utcnow()
    user = await session.scalar(select(User).where(User.email == data.email))

    if user is not None and user.locked_until is not None and user.locked_until > now:
        retry_after = max(1, int((user.locked_until - now).total_seconds()))
        raise TooManyRequests(
            "Too many failed sign-in attempts. Please wait a few minutes and try again.",
            code="too_many_attempts",
            headers={"Retry-After": str(retry_after)},
        )

    # Always verify something, so response time does not reveal whether the e-mail exists.
    valid, upgraded_hash = await asyncio.to_thread(
        verify_password, data.password, user.password_hash if user is not None else dummy_hash()
    )
    if user is None or not valid or not user.is_active:
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.login_max_failed_attempts:
                user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
                user.failed_login_attempts = 0
            await session.commit()
        raise Unauthorized("Incorrect email or password.", code="invalid_credentials")

    user.failed_login_attempts, user.locked_until = 0, None
    if upgraded_hash:
        user.password_hash = upgraded_hash
    await session.execute(delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at < now))
    token = await _open_session(session, user.id, user_agent, ip)
    await session.commit()
    return user, token


async def logout(session: AsyncSession, token: str | None) -> None:
    if token:
        await session.execute(delete(AuthSession).where(AuthSession.token_hash == hash_token(token)))
        await session.commit()


async def authenticate(session: AsyncSession, token: str) -> User | None:
    """The active user owning a live session, or None. Slides the expiry forward (at most every 5 minutes)."""
    now = utcnow()
    row = (
        await session.execute(
            select(AuthSession, User)
            .join(User, User.id == AuthSession.user_id)
            .where(AuthSession.token_hash == hash_token(token), AuthSession.expires_at > now, User.is_active)
        )
    ).first()
    if row is None:
        return None
    auth_session, user = row
    if now - auth_session.last_seen_at > _TOUCH_INTERVAL:
        await session.execute(
            update(AuthSession)
            .where(AuthSession.id == auth_session.id)
            .values(last_seen_at=now, expires_at=now + timedelta(hours=get_settings().session_ttl_hours))
        )
        await session.commit()
    return user


async def purge_expired_sessions(session: AsyncSession) -> None:
    await session.execute(delete(AuthSession).where(AuthSession.expires_at < utcnow()))
    await session.commit()


async def _open_session(session: AsyncSession, user_id: uuid.UUID, user_agent: str | None, ip: str | None) -> str:
    token = new_session_token()
    session.add(
        AuthSession(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=utcnow() + timedelta(hours=get_settings().session_ttl_hours),
            user_agent=(user_agent or "")[:255] or None,
            ip_address=ip,
        )
    )
    return token
