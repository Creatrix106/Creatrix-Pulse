"""Test harness: a real PostgreSQL database, the real Alembic migrations, the real ASGI app.

Set TEST_DATABASE_URL to point at any PostgreSQL server you may create databases on, e.g.
    TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/creatrix_test
The database named in the URL is dropped and re-created at the start of the run.
"""

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import psycopg
import pytest
import pytest_asyncio
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/creatrix_test")

# Must be set before `app` is imported anywhere: settings are read once.
os.environ.update(
    DATABASE_URL=TEST_DATABASE_URL,
    ENVIRONMENT="test",
    CORS_ORIGINS="http://localhost:3000",
    LOG_LEVEL="WARNING",
    API_PREFIX="/api",
    LOGIN_MAX_FAILED_ATTEMPTS="5",
    PROCESSING_STALE_SECONDS="60",
    MAX_UPLOAD_MB="2",
)


def _admin_conninfo() -> tuple[str, str]:
    url = make_url(TEST_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1))
    admin = (
        url.set(database="postgres")
        .render_as_string(hide_password=False)
        .replace("postgresql+psycopg://", "postgresql://")
    )
    return admin, str(url.database)


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    admin, name = _admin_conninfo()
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    # Exercise the real migrations rather than metadata.create_all().
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        env=os.environ.copy(),
    )


@pytest.fixture(scope="session", autouse=True)
def fast_password_hashing() -> None:
    """Argon2 at production strength costs ~0.2 s per hash; tests only need the code path, not the cost."""
    from app.core import security
    from pwdlib import PasswordHash
    from pwdlib.hashers.argon2 import Argon2Hasher

    security._hasher = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=1024, parallelism=1),))
    security.dummy_hash.cache_clear()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def app(database):
    from app.main import app as fastapi_app

    async with fastapi_app.router.lifespan_context(fastapi_app):
        yield fastapi_app


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_state(app):
    """Every test starts from an empty database and an empty analytics cache."""
    from app.db.session import get_sessionmaker
    from app.services.analytics.frames import get_frame_cache
    from app.services.jobs import jobs
    from sqlalchemy import text

    await jobs.wait_idle(timeout=30)
    async with get_sessionmaker()() as session:
        await session.execute(text("TRUNCATE users CASCADE"))
        await session.commit()
    get_frame_cache().clear()
    yield
    await jobs.wait_idle(timeout=30)


def new_client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000", headers={"Accept": "application/json"}
    )


@pytest_asyncio.fixture(loop_scope="session")
async def anon(app) -> AsyncIterator[httpx.AsyncClient]:
    async with new_client(app) as client:
        yield client


async def register(client: httpx.AsyncClient, *, email: str | None = None, role: str | None = None) -> dict:
    email = email or f"user-{uuid.uuid4().hex[:10]}@example.com"
    response = await client.post(
        "/api/auth/register", json={"name": "Test User", "email": email, "password": "Passw0rdOK"}
    )
    assert response.status_code == 201, response.text
    user = response.json()
    if role:
        from app.db.models import User
        from app.db.session import get_sessionmaker
        from sqlalchemy import update

        async with get_sessionmaker()() as session:
            await session.execute(update(User).where(User.email == email).values(role=role))
            await session.commit()
        user["role"] = role
    return user


@pytest_asyncio.fixture(loop_scope="session")
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    """A client signed in as a fresh admin user."""
    async with new_client(app) as c:
        c.user = await register(c)  # type: ignore[attr-defined]
        yield c


@pytest_asyncio.fixture(loop_scope="session")
async def other_client(app) -> AsyncIterator[httpx.AsyncClient]:
    """A second, independent signed-in user (for isolation tests)."""
    async with new_client(app) as c:
        c.user = await register(c)  # type: ignore[attr-defined]
        yield c
