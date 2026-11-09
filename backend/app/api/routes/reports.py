import asyncio
import re
from urllib.parse import quote

from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, SessionDep, WriterUser
from app.api.routes.analytics import load_context
from app.core.config import get_settings
from app.core.errors import NotFound
from app.schemas.report import ReportConfigIn, ReportPreviewOut, ReportRecordOut
from app.services import datasets as dataset_service
from app.services import reports as report_service
from app.services.analytics.context import AnalyticsContext
from app.services.analytics.formatting import Formatters

router = APIRouter(prefix="/datasets/{dataset_id}/reports", tags=["reports"])

_MEDIA_TYPES = {"csv": "text/csv; charset=utf-8", "json": "application/json; charset=utf-8"}


async def _context(session: SessionDep, user: CurrentUser, dataset_id: str) -> AnalyticsContext:
    settings = get_settings()
    # Reports contain no formatted text, but the context requires formatters.
    return await load_context(
        session, user, dataset_id, Formatters.create(settings.default_currency, settings.default_locale)
    )


@router.post("/preview", response_model=ReportPreviewOut, summary="Preview a report without saving it")
async def preview_report(
    dataset_id: str, config: ReportConfigIn, user: CurrentUser, session: SessionDep
) -> ReportPreviewOut:
    ctx = await _context(session, user, dataset_id)
    return await asyncio.to_thread(report_service.build_preview, ctx, config)


@router.get("", response_model=list[ReportRecordOut], summary="Report history for a dataset, newest first")
async def list_reports(dataset_id: str, user: CurrentUser, session: SessionDep) -> list[ReportRecordOut]:
    dataset = await dataset_service.get_owned(session, user.id, dataset_id)
    return await report_service.list_reports(session, dataset)


@router.post("", response_model=ReportRecordOut, status_code=201, summary="Generate and save a report")
async def create_report(
    dataset_id: str, config: ReportConfigIn, user: WriterUser, session: SessionDep
) -> ReportRecordOut:
    dataset = await dataset_service.get_ready(session, user.id, dataset_id)
    ctx = await _context(session, user, dataset_id)
    preview = await asyncio.to_thread(report_service.build_preview, ctx, config)  # the pandas part
    return await report_service.create_report(session, dataset, preview, config)


@router.get("/{report_id}/download", summary="Download a saved report as a file")
async def download_report(dataset_id: str, report_id: str, user: CurrentUser, session: SessionDep) -> Response:
    dataset = await dataset_service.get_owned(session, user.id, dataset_id)
    report = await report_service.get_report(session, dataset, report_id)
    if report is None:
        raise NotFound("This report does not exist or was deleted.", code="report_not_found")
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", report.title).strip("-") or "report"
    filename = f"{base}.{report.format}"
    return Response(
        content=report.content.encode("utf-8"),
        media_type=_MEDIA_TYPES[report.format],
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"},
    )
