"""Custom reports: preview, persistence and CSV/JSON rendering (port of src/services/mock/reports.mock.ts)."""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Unprocessable
from app.db.models import Dataset, Report
from app.schemas.analytics import DatePeriod
from app.schemas.report import (
    ReportColumn,
    ReportConfigIn,
    ReportPreviewOut,
    ReportRecordOut,
    ReportSummaryItem,
)
from app.services.analytics.context import AnalyticsContext
from app.services.analytics.metrics import fill_keys, time_series, totals
from app.services.analytics.slicing import AnalyticsFilters, slice_frame


@dataclass(frozen=True, slots=True)
class MetricOption:
    key: str
    label: str
    format: str
    requires_cost: bool = False


#: Same order and labels as METRIC_OPTIONS in the frontend (src/config/filters.ts).
METRICS: tuple[MetricOption, ...] = (
    MetricOption("revenue", "Revenue", "currency"),
    MetricOption("orders", "Orders", "number"),
    MetricOption("units", "Units sold", "number"),
    MetricOption("aov", "Average order value", "currency"),
    MetricOption("cost", "Cost", "currency", requires_cost=True),
    MetricOption("profit", "Gross profit", "currency", requires_cost=True),
)
PRESET_LABELS = {
    "all": "All time",
    "last_30d": "Last 30 days",
    "last_90d": "Last 90 days",
    "last_180d": "Last 180 days",
    "ytd": "Year to date",
    "custom": "Custom range",
}


def build_preview(ctx: AnalyticsContext, config: ReportConfigIn) -> ReportPreviewOut:
    sliced = slice_frame(
        ctx.frame, AnalyticsFilters(date_preset=config.date_preset, comparison="none", group_by="month")
    )
    metrics = [m for m in METRICS if m.key in config.metrics and not (m.requires_cost and not ctx.has_cost)]
    if not metrics:
        raise Unprocessable("None of the selected metrics are available for this dataset.", code="no_valid_metrics")

    series = time_series(
        sliced.current,
        "month",
        fill=fill_keys((sliced.range_from, sliced.range_to), ctx.span, "month"),
        has_cost=ctx.has_cost and not sliced.current.empty,
    )
    t = totals(sliced.current)
    summary_values = {
        "revenue": t.revenue,
        "orders": t.orders,
        "units": t.units,
        "aov": t.aov,
        "cost": t.cost or 0,
        "profit": t.profit or 0,
    }
    return ReportPreviewOut(
        title=config.title,
        generated_at=datetime.now(UTC),
        period=DatePeriod(from_=sliced.range_from, to=sliced.range_to),
        summary=[
            ReportSummaryItem(label=m.label, value=round(float(summary_values[m.key]), 2), format=m.format)
            for m in metrics
        ],
        columns=[
            ReportColumn(key="date", label="Month", format="date"),
            *[ReportColumn(key=m.key, label=m.label, format=m.format) for m in metrics],
        ],
        rows=[{"date": p.date.isoformat(), **{m.key: getattr(p, m.key) or 0 for m in metrics}} for p in series],
    )


# ------------------------------------------------------------------------------------- rendering
def _cell(value: object) -> str:
    """``String(value)`` + RFC-4180 escaping, exactly like toCsv in the frontend (src/utils/csv.ts)."""
    if value is None:
        text = ""
    elif isinstance(value, float):
        text = str(int(value)) if value == int(value) else repr(value)
    else:
        text = str(value)
    return '"' + text.replace('"', '""') + '"' if any(ch in text for ch in '",\n\r') else text


def render_content(preview: ReportPreviewOut, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(preview.model_dump(mode="json"), indent=2, ensure_ascii=False)
    lines: list[list[object]] = [[c.label for c in preview.columns]]
    lines += [[row[c.key] for c in preview.columns] for row in preview.rows]
    return "\n".join(",".join(_cell(value) for value in line) for line in lines)


# ----------------------------------------------------------------------------------- persistence
def download_url(dataset_id: uuid.UUID, report_id: uuid.UUID) -> str:
    settings = get_settings()
    path = f"/datasets/{dataset_id}/reports/{report_id}/download"
    return (settings.public_api_url.rstrip("/") if settings.public_api_url else settings.api_prefix) + path


def to_record(report: Report) -> ReportRecordOut:
    return ReportRecordOut(
        id=str(report.id),
        dataset_id=str(report.dataset_id),
        title=report.title,
        format=report.format,
        created_at=report.created_at,
        row_count=report.row_count,
        size_bytes=report.size_bytes,
        content=report.content,
        download_url=download_url(report.dataset_id, report.id),
    )


async def create_report(
    session: AsyncSession, dataset: Dataset, preview: ReportPreviewOut, config: ReportConfigIn
) -> ReportRecordOut:
    content = render_content(preview, config.format)
    report = Report(
        dataset_id=dataset.id,
        owner_id=dataset.owner_id,
        title=f"{config.title} ({PRESET_LABELS.get(config.date_preset, config.date_preset)})",
        format=config.format,
        config=config.model_dump(mode="json"),
        content=content,
        row_count=len(preview.rows),
        size_bytes=len(content.encode("utf-8")),
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return to_record(report)


async def list_reports(session: AsyncSession, dataset: Dataset) -> list[ReportRecordOut]:
    result = await session.scalars(
        select(Report).where(Report.dataset_id == dataset.id).order_by(Report.created_at.desc(), Report.id.desc())
    )
    return [to_record(report) for report in result]


async def get_report(session: AsyncSession, dataset: Dataset, report_id: str) -> Report | None:
    try:
        parsed = uuid.UUID(report_id)
    except ValueError:
        return None
    return await session.scalar(select(Report).where(Report.id == parsed, Report.dataset_id == dataset.id))
