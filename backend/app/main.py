"""Application factory.

Run with:  uvicorn app.main:app            (development: add --reload)
           alembic upgrade head            (create/upgrade the database schema first)
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.types import Scope

from app.api.routes import analytics, auth, datasets, health, reports
from app.core.config import get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    BodySizeLimitMiddleware,
    CatchAllErrorsMiddleware,
    OriginCheckMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.session import dispose_engine, get_sessionmaker
from app.services import auth as auth_service
from app.services.analytics.frames import get_frame_cache
from app.services.jobs import jobs

log = logging.getLogger("app")

_JSON_BODY_LIMIT = 1024 * 1024  # every endpoint except the upload takes tiny JSON bodies
_MULTIPART_OVERHEAD = 1024 * 1024  # boundaries, the mapping field, headers


async def _wait_for_database(attempts: int = 10, delay: float = 1.0) -> None:
    """The database may still be starting (docker compose): retry briefly, then fail loudly."""
    for attempt in range(1, attempts + 1):
        try:
            async with get_sessionmaker()() as session:
                await session.execute(text("SELECT 1"))
            return
        except Exception as exc:
            if attempt == attempts:
                raise RuntimeError("Cannot connect to the database. Check DATABASE_URL.") from exc
            log.warning("Database not reachable yet (%s/%s): %s", attempt, attempts, exc.__class__.__name__)
            await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    log.info("Starting %s [%s]", settings.app_name, settings.environment)
    await _wait_for_database()
    async with get_sessionmaker()() as session:
        await auth_service.purge_expired_sessions(session)
    yield
    log.info("Shutting down: waiting for background jobs")
    await jobs.shutdown(timeout=10)
    get_frame_cache().clear()
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    prefix = settings.api_prefix
    docs = settings.effective_docs_enabled

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        summary="Backend for the Creatrix Pulse sales-analytics dashboard.",
        lifespan=lifespan,
        docs_url=f"{prefix}/docs" if docs else None,
        redoc_url=None,
        openapi_url=f"{prefix}/openapi.json" if docs else None,
    )
    install_exception_handlers(app)

    upload_path = f"{prefix}/datasets"

    def body_limit(scope: Scope) -> int:
        is_upload = scope["method"] == "POST" and scope["path"].rstrip("/") == upload_path
        return settings.max_upload_bytes + _MULTIPART_OVERHEAD if is_upload else _JSON_BODY_LIMIT

    # Starlette wraps in reverse: the LAST added middleware is the OUTERMOST.
    app.add_middleware(CatchAllErrorsMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware, limit_for=body_limit)
    app.add_middleware(OriginCheckMiddleware, allowed_origins=settings.cors_origins)
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,  # the session cookie travels with fetch(..., { credentials: "include" })
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Content-Disposition"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)

    for router in (auth.router, datasets.router, analytics.router, reports.router, health.router):
        app.include_router(router, prefix=prefix)
    app.include_router(health.router, include_in_schema=False)  # /health for orchestrator probes
    return app


app = create_app()
