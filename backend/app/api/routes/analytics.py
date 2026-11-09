import asyncio
from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.errors import Unprocessable
from app.schemas.analytics import (
    CustomersData,
    ExplorerData,
    FinanceData,
    OverviewData,
    ProductsData,
    SalesData,
)
from app.schemas.common import CapabilityAvailable, CapabilityUnavailable, ComparisonMode, DatePreset, GroupBy
from app.schemas.insight import Insight
from app.services import datasets as dataset_service
from app.services.analytics import dashboards
from app.services.analytics.context import AnalyticsContext
from app.services.analytics.explorer import explorer_data
from app.services.analytics.formatting import Formatters
from app.services.analytics.frames import get_frame_cache, load_frame
from app.services.analytics.insights import build_insights
from app.services.analytics.slicing import AnalyticsFilters, Sliced, slice_frame

router = APIRouter(prefix="/datasets/{dataset_id}", tags=["analytics"])


def analytics_filters(
    date_preset: Annotated[DatePreset, Query(alias="datePreset")] = "all",
    date_from: Annotated[date | None, Query(alias="dateFrom", description="ISO date, with datePreset=custom")] = None,
    date_to: Annotated[date | None, Query(alias="dateTo", description="ISO date, with datePreset=custom")] = None,
    comparison: ComparisonMode = "none",
    group_by: Annotated[GroupBy, Query(alias="groupBy")] = "month",
    categories: Annotated[list[str] | None, Query(description="Repeat the parameter for several values")] = None,
    regions: Annotated[list[str] | None, Query(description="Repeat the parameter for several values")] = None,
) -> AnalyticsFilters:
    if date_from and date_to and date_from > date_to:
        raise Unprocessable("The start date must be on or before the end date.", code="invalid_date_range")
    return AnalyticsFilters(
        date_preset=date_preset,
        date_from=date_from,
        date_to=date_to,
        comparison=comparison,
        group_by=group_by,
        categories=tuple(categories or ()),
        regions=tuple(regions or ()),
    )


def text_formatters(
    currency: Annotated[
        str | None, Query(min_length=3, max_length=3, description="ISO 4217 code for insight text")
    ] = None,
    locale: Annotated[str | None, Query(max_length=16, description="BCP 47 tag for insight text, e.g. en-IN")] = None,
) -> Formatters:
    """Insights are phrased by the server, so it needs the user's currency/locale (defaults: INR / en-IN, the
    frontend's defaults). The current UI does not send these, so its insights are always in rupees."""
    settings = get_settings()
    try:
        return Formatters.create(currency or settings.default_currency, locale or settings.default_locale)
    except ValueError as exc:
        raise Unprocessable(str(exc), code="invalid_format_settings") from None


FiltersDep = Annotated[AnalyticsFilters, Depends(analytics_filters)]
FormattersDep = Annotated[Formatters, Depends(text_formatters)]


async def load_context(
    session: SessionDep, user: CurrentUser, dataset_id: str, formatters: Formatters
) -> AnalyticsContext:
    dataset = await dataset_service.get_ready(session, user.id, dataset_id)
    frame = await get_frame_cache().get_or_load(dataset.id, lambda: load_frame(session, dataset.id))
    return AnalyticsContext(
        frame=frame,
        has_customers=dataset.has_customers,
        has_cost=dataset.has_cost,
        has_regions=dataset.has_regions,
        formatters=formatters,
    )


async def _compute(
    builder: Callable[[AnalyticsContext, Sliced], Any],
    session: SessionDep,
    user: CurrentUser,
    dataset_id: str,
    filters: AnalyticsFilters,
    formatters: Formatters,
) -> Any:
    ctx = await load_context(session, user, dataset_id, formatters)
    # pandas work is CPU-bound: keep it off the event loop so other requests stay responsive.
    return await asyncio.to_thread(lambda: builder(ctx, slice_frame(ctx.frame, filters)))


@router.get(
    "/analytics/overview",
    response_model=OverviewData,
    summary="KPIs, revenue trend, top products, breakdowns, insights",
)
async def overview(
    dataset_id: str, user: CurrentUser, session: SessionDep, filters: FiltersDep, fmt: FormattersDep
) -> Any:
    return await _compute(dashboards.overview, session, user, dataset_id, filters, fmt)


@router.get(
    "/analytics/sales", response_model=SalesData, summary="Sales KPIs, trend, previous-period trend, category trend"
)
async def sales(
    dataset_id: str, user: CurrentUser, session: SessionDep, filters: FiltersDep, fmt: FormattersDep
) -> Any:
    return await _compute(dashboards.sales, session, user, dataset_id, filters, fmt)


@router.get("/analytics/products", response_model=ProductsData, summary="Product performance")
async def products(
    dataset_id: str, user: CurrentUser, session: SessionDep, filters: FiltersDep, fmt: FormattersDep
) -> Any:
    return await _compute(dashboards.products, session, user, dataset_id, filters, fmt)


@router.get(
    "/analytics/customers",
    response_model=CapabilityAvailable[CustomersData] | CapabilityUnavailable,
    summary="Customer analytics (available=false when the file has no customer column)",
)
async def customers(
    dataset_id: str, user: CurrentUser, session: SessionDep, filters: FiltersDep, fmt: FormattersDep
) -> Any:
    return await _compute(dashboards.customers, session, user, dataset_id, filters, fmt)


@router.get(
    "/analytics/finance",
    response_model=CapabilityAvailable[FinanceData] | CapabilityUnavailable,
    summary="Profit and margin analytics (available=false when the file has no cost column)",
)
async def finance(
    dataset_id: str, user: CurrentUser, session: SessionDep, filters: FiltersDep, fmt: FormattersDep
) -> Any:
    return await _compute(dashboards.finance, session, user, dataset_id, filters, fmt)


@router.get("/analytics/insights", response_model=list[Insight], summary="All automatic insights for the selection")
async def insights(
    dataset_id: str, user: CurrentUser, session: SessionDep, filters: FiltersDep, fmt: FormattersDep
) -> Any:
    return await _compute(build_insights, session, user, dataset_id, filters, fmt)


@router.get("/records", response_model=ExplorerData, summary="Cleaned records for the Data Explorer (newest first)")
async def records(
    dataset_id: str,
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=get_settings().explorer_max_rows)] = get_settings().explorer_max_rows,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Response:
    dataset = await dataset_service.get_ready(session, user.id, dataset_id)
    data = await explorer_data(session, dataset, limit=limit, offset=offset)
    # Up to 50,000 rows: serialise once with pydantic's Rust encoder and skip FastAPI's second validation pass.
    return Response(data.model_dump_json(by_alias=True), media_type="application/json")
