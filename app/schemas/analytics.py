import datetime as dt
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel, is_none
from app.schemas.insight import Insight

KpiFormat = Literal["currency", "number", "percent"]


class Kpi(CamelModel):
    id: str
    label: str
    value: float
    format: KpiFormat
    #: % change vs the comparison period (percentage points for percent KPIs); null = no comparison. why ? because of maths
    change: float | None = None
    inverse: bool | None = Field(None, exclude_if=is_none)
    hint: str | None = Field(None, exclude_if=is_none)


class TimeSeriesPoint(CamelModel):
    date: dt.date
    revenue: float
    orders: int
    units: float
    aov: float
    # Present only when the dataset has cost information.
    cost: float | None = Field(None, exclude_if=is_none)
    profit: float | None = Field(None, exclude_if=is_none)
    margin: float | None = Field(None, exclude_if=is_none)


class BreakdownItem(CamelModel):
    name: str
    value: float
    #: Share of total, 0-100.
    share: float
    change: float | None = None
    secondary: float | None = Field(None, exclude_if=is_none)


class ProductPerformance(CamelModel):
    id: str
    name: str
    category: str
    revenue: float
    units: float
    orders: int
    share: float
    change: float | None = None
    margin: float | None = None


class DatePeriod(CamelModel):
    from_: dt.date = Field(alias="from")
    to: dt.date


class OverviewData(CamelModel):
    period: DatePeriod
    kpis: list[Kpi]
    revenue_trend: list[TimeSeriesPoint]
    top_products: list[ProductPerformance]
    categories: list[BreakdownItem]
    regions: list[BreakdownItem]
    insights: list[Insight]


class CategoryTrendPoint(CamelModel):
    date: dt.date
    values: dict[str, float]


class SalesData(CamelModel):
    kpis: list[Kpi]
    trend: list[TimeSeriesPoint]
    previous_trend: list[TimeSeriesPoint] | None
    categories: list[BreakdownItem]
    regions: list[BreakdownItem]
    category_names: list[str]
    category_trend: list[CategoryTrendPoint]


class ProductsData(CamelModel):
    top: list[ProductPerformance]
    low: list[ProductPerformance]
    all: list[ProductPerformance]
    categories: list[BreakdownItem]


class CustomerSegment(CamelModel):
    name: str
    description: str
    customers: int
    revenue: float
    share: float


class NewVsReturningPoint(CamelModel):
    date: dt.date
    new_customers: int
    returning_customers: int


class FrequencyBin(CamelModel):
    label: str
    count: int


class CustomersData(CamelModel):
    kpis: list[Kpi]
    new_vs_returning: list[NewVsReturningPoint]
    distribution: list[BreakdownItem]
    frequency: list[FrequencyBin]
    segments: list[CustomerSegment]


class FinanceData(CamelModel):
    kpis: list[Kpi]
    trend: list[TimeSeriesPoint]
    category_margins: list[BreakdownItem]


class ExplorerColumn(CamelModel):
    key: str
    label: str
    type: Literal["string", "number", "date"]
    format: Literal["currency"] | None = Field(None, exclude_if=is_none)


class ExplorerData(CamelModel):
    columns: list[ExplorerColumn]
    rows: list[dict[str, str | int | float | None]]
    # Paging metadata (additive – the current UI ignores it and filters client-side).
    total: int
    truncated: bool
    limit: int
    offset: int
