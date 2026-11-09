from fastapi import APIRouter, Response
from sqlalchemy import text

from app.db.session import get_sessionmaker

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness: the process is up")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness: the database answers")
async def readiness(response: Response) -> dict[str, str]:
    try:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "degraded", "database": "down"}
    return {"status": "ok", "database": "up"}
