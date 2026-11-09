import datetime as dt
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from app.schemas.analytics import DatePeriod
from app.schemas.common import CamelModel, DatePreset, MetricKey

ReportFormat = Literal["csv", "json"]


class ReportConfigIn(CamelModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    metrics: Annotated[list[MetricKey], Field(min_length=1)]
    date_preset: DatePreset
    format: ReportFormat

    @field_validator("title", mode="after")
    @classmethod
    def _printable(cls, value: str) -> str:
        return "".join(ch for ch in value if ch.isprintable())


class ReportSummaryItem(CamelModel):
    label: str
    value: float
    format: Literal["currency", "number", "percent"]


class ReportColumn(CamelModel):
    key: str
    label: str
    format: Literal["date", "currency", "number"]


class ReportPreviewOut(CamelModel):
    title: str
    generated_at: dt.datetime
    period: DatePeriod
    summary: list[ReportSummaryItem]
    columns: list[ReportColumn]
    rows: list[dict[str, str | int | float]]


class ReportRecordOut(CamelModel):
    id: str
    dataset_id: str
    title: str
    format: ReportFormat
    created_at: dt.datetime
    row_count: int
    size_bytes: int
    #: Inline content so the current UI can download without another request (its `download()` reads this).
    content: str | None = None
    #: Authenticated download endpoint (Content-Disposition: attachment).
    download_url: str | None = None
