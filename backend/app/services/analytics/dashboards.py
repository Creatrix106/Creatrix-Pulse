"""The five dashboard payloads (overview, sales, products, customers, finance).

Ported from ``mockAnalyticsService`` in the frontend (src/services/mock/analytics.mock.ts), computed with
pandas over the dataset's in-memory frame. Intentional differences from the mock, all for real-world files:

* time series are zero-filled over the selected window (days without sales are real zeros, and the
  "previous period" overlay is aligned *by position* by the UI, so gaps must not shift it);
* orders are counted as *distinct order ids* everywhere (a file may have several lines per order);
* revenue-per-customer only counts rows that have a customer.
"""

import numpy as np
import pandas as pd

from app.schemas.analytics import (
    BreakdownItem,
    CategoryTrendPoint,
    CustomersData,
    CustomerSegment,
    DatePeriod,
    FinanceData,
    FrequencyBin,
    Kpi,
    KpiFormat,
    NewVsReturningPoint,
    OverviewData,
    ProductsData,
    SalesData,
    TimeSeriesPoint,
)
from app.schemas.common import CapabilityAvailable, CapabilityUnavailable
from app.services.analytics.context import AnalyticsContext
from app.services.analytics.formatting import to_fixed
from app.services.analytics.insights import build_insights
from app.services.analytics.metrics import (
    Totals,
    breakdown,
    bucket_days,
    day_number_to_date,
    fill_keys,
    margins_by_category,
    money,
    pct_change,
    product_performance,
    ratio,
    time_series,
    totals,
)
from app.services.analytics.slicing import Sliced

NO_CUSTOMERS = (
    "This dataset has no customer column. Map a customer ID column when uploading to unlock customer analytics."
)
NO_COST = (
    "This dataset has no cost column, so profit and margin cannot be calculated. "
    "Map a cost column when uploading to unlock financial analytics."
)


# ----------------------------------------------------------------------------------------- KPIs
def _kpi(
    id: str,
    label: str,
    value: float,
    fmt: KpiFormat,
    change: float | None,
    *,
    inverse: bool | None = None,
    hint: str | None = None,
) -> Kpi:
    rounded = money(value) if fmt == "currency" else round(float(value), 4)
    return Kpi(id=id, label=label, value=rounded, format=fmt, change=ratio(change), inverse=inverse, hint=hint)


def core_kpis(cur: Totals, prev: Totals | None) -> list[Kpi]:
    return [
        _kpi("revenue", "Revenue", cur.revenue, "currency", pct_change(cur.revenue, prev.revenue if prev else None)),
        _kpi("orders", "Orders", cur.orders, "number", pct_change(cur.orders, prev.orders if prev else None)),
        _kpi("units", "Units sold", cur.units, "number", pct_change(cur.units, prev.units if prev else None)),
        _kpi("aov", "Avg. order value", cur.aov, "currency", pct_change(cur.aov, prev.aov if prev else None)),
    ]


def profit_kpis(cur: Totals, prev: Totals | None) -> list[Kpi]:
    if cur.profit is None or cur.margin is None:
        return []
    return [
        _kpi("profit", "Gross profit", cur.profit, "currency", pct_change(cur.profit, prev.profit if prev else None)),
        _kpi(
            "margin",
            "Profit margin",
            cur.margin,
            "percent",
            cur.margin - prev.margin if prev is not None and prev.margin is not None else None,
            hint="Change in percentage points",
        ),
    ]


def _totals_pair(sliced: Sliced) -> tuple[Totals, Totals | None]:
    return totals(sliced.current), totals(sliced.previous) if sliced.previous is not None else None


def _series(ctx: AnalyticsContext, sliced: Sliced, *, previous: bool = False) -> list[TimeSeriesPoint]:
    df = sliced.previous if previous else sliced.current
    if df is None:
        return []
    group_by = sliced.filters.group_by
    window = sliced.previous_range if previous else (sliced.range_from, sliced.range_to)
    has_cost = ctx.has_cost and bool(df["cost"].notna().all())
    keys = fill_keys(window, ctx.span, group_by, clamp_start=not previous)
    return time_series(df, group_by, fill=keys, has_cost=has_cost)


# --------------------------------------------------------------------------------------- overview
def overview(ctx: AnalyticsContext, sliced: Sliced) -> OverviewData:
    cur, prev = _totals_pair(sliced)
    return OverviewData(
        period=DatePeriod(from_=sliced.range_from, to=sliced.range_to),
        kpis=[*core_kpis(cur, prev), *profit_kpis(cur, prev)],
        revenue_trend=_series(ctx, sliced),
        top_products=product_performance(sliced.current, sliced.previous, has_cost=ctx.has_cost)[:5],
        categories=breakdown(sliced.current, "category", sliced.previous),
        regions=breakdown(sliced.current, "region", sliced.previous),
        insights=build_insights(ctx, sliced)[:4],
    )


# ------------------------------------------------------------------------------------------ sales
def sales(ctx: AnalyticsContext, sliced: Sliced) -> SalesData:
    cur, prev = _totals_pair(sliced)
    categories = breakdown(sliced.current, "category", sliced.previous)
    group_by = sliced.filters.group_by
    return SalesData(
        kpis=core_kpis(cur, prev),
        trend=_series(ctx, sliced),
        previous_trend=_series(ctx, sliced, previous=True) if sliced.previous is not None else None,
        categories=categories,
        regions=breakdown(sliced.current, "region", sliced.previous),
        category_names=[c.name for c in categories],
        category_trend=_category_trend(ctx, sliced, group_by),
    )


def _category_trend(ctx: AnalyticsContext, sliced: Sliced, group_by: str) -> list[CategoryTrendPoint]:
    df = sliced.current
    if df.empty or not ctx.frame.has_category:
        return []
    work = pd.DataFrame(
        {
            "k": bucket_days(df["date"].to_numpy(), group_by),
            "category": df["category"].astype(object).to_numpy(),
            "revenue": df["revenue"].to_numpy(),
        }
    ).dropna(subset=["category"])
    sums = work.groupby(["k", "category"], as_index=False)["revenue"].sum()
    by_bucket: dict[int, dict[str, float]] = {}
    for key, category, revenue in zip(
        sums["k"].to_numpy(dtype="int64"),
        sums["category"].to_numpy(),
        sums["revenue"].to_numpy(dtype="float64"),
        strict=True,
    ):
        by_bucket.setdefault(int(key), {})[str(category)] = money(float(revenue))
    keys = fill_keys((sliced.range_from, sliced.range_to), ctx.span, group_by)
    ordered = sorted(by_bucket) if keys is None else [int(k) for k in keys]
    return [CategoryTrendPoint(date=day_number_to_date(k), values=by_bucket.get(k, {})) for k in ordered]


# ---------------------------------------------------------------------------------------- products
def products(ctx: AnalyticsContext, sliced: Sliced) -> ProductsData:
    every = product_performance(sliced.current, sliced.previous, has_cost=ctx.has_cost)
    return ProductsData(
        all=every,
        top=every[:5],
        low=list(reversed(every))[:5],  # lowest revenue first
        categories=breakdown(sliced.current, "category", sliced.previous),
    )


# --------------------------------------------------------------------------------------- customers
_FREQUENCY_LABELS = ("1 order", "2 orders", "3 orders", "4 orders", "5 orders", "6+ orders")
_SEGMENTS = (
    ("Champions", "6 or more orders", 6, 10**9),
    ("Loyal", "3–5 orders", 3, 5),
    ("Returning", "2 orders", 2, 2),
    ("One-time", "1 order", 1, 1),
)


def customers(ctx: AnalyticsContext, sliced: Sliced) -> CapabilityAvailable[CustomersData] | CapabilityUnavailable:
    if not ctx.has_customers:
        return CapabilityUnavailable(reason=NO_CUSTOMERS)
    group_by = sliced.filters.group_by
    cur = sliced.current.dropna(subset=["customer"])
    prev = sliced.previous.dropna(subset=["customer"]) if sliced.previous is not None else None

    # First purchase of every customer within the category/region scope, over *all* dates.
    first = sliced.scoped().dropna(subset=["customer"]).groupby("customer", observed=True)["date"].min()
    stats = cur.groupby("customer", observed=True).agg(orders=("order_code", "nunique"), revenue=("revenue", "sum"))
    total = len(stats)

    new_count = int((first.reindex(stats.index) >= pd.Timestamp(sliced.range_from)).sum()) if total else 0
    per_customer = float(cur["revenue"].sum()) / total if total else 0.0
    prev_total = int(prev["customer"].nunique()) if prev is not None else None
    prev_per_customer = float(prev["revenue"].sum()) / prev_total if prev is not None and prev_total else None

    orders = stats["orders"].to_numpy()
    revenue = stats["revenue"].to_numpy()
    frequency = np.bincount(np.minimum(orders, 6), minlength=7)[1:7] if total else np.zeros(6, dtype=int)
    segments = []
    for name, description, low, high in _SEGMENTS:
        in_segment = (orders >= low) & (orders <= high)
        count = int(in_segment.sum())
        segments.append(
            CustomerSegment(
                name=name,
                description=description,
                customers=count,
                revenue=money(revenue[in_segment].sum()),
                share=round(count / total * 100, 4) if total else 0.0,
            )
        )

    distribution: list[BreakdownItem] = []
    if ctx.has_regions and total:
        by_region = cur.dropna(subset=["region"]).groupby("region", observed=True)["customer"].nunique()
        by_region.index = by_region.index.astype(object)
        for region, count in by_region.sort_values(ascending=False, kind="stable").items():
            distribution.append(
                BreakdownItem(name=str(region), value=float(count), share=round(float(count) / total * 100, 4))
            )

    data = CustomersData(
        kpis=[
            _kpi("customers", "Total customers", total, "number", pct_change(total, prev_total)),
            _kpi("new", "New customers", new_count, "number", None),
            _kpi("returning", "Returning customers", total - new_count, "number", None),
            _kpi("rpc", "Revenue per customer", per_customer, "currency", pct_change(per_customer, prev_per_customer)),
        ],
        new_vs_returning=_new_vs_returning(ctx, sliced, cur, first, group_by),
        distribution=distribution,
        frequency=[
            FrequencyBin(label=label, count=int(n)) for label, n in zip(_FREQUENCY_LABELS, frequency, strict=True)
        ],
        segments=segments,
    )
    return CapabilityAvailable[CustomersData](data=data)


def _new_vs_returning(
    ctx: AnalyticsContext, sliced: Sliced, cur: pd.DataFrame, first: pd.Series, group_by: str
) -> list[NewVsReturningPoint]:
    if cur.empty:
        return []
    customer = cur["customer"]
    first_by_code = first.reindex(customer.cat.categories)  # first purchase per category code (NaT = not in scope)
    first_bucket = bucket_days(first_by_code.to_numpy(), group_by)

    # distinct (bucket, customer) pairs → a customer is "new" in the bucket that holds their first purchase
    pairs = pd.DataFrame(
        {"b": bucket_days(cur["date"].to_numpy(), group_by), "c": customer.cat.codes.to_numpy()}
    ).drop_duplicates()
    is_new = first_bucket[pairs["c"].to_numpy()] == pairs["b"].to_numpy()
    active = pairs.groupby("b").size()
    fresh = pairs[is_new].groupby("b").size().reindex(active.index, fill_value=0)

    keys = fill_keys((sliced.range_from, sliced.range_to), ctx.span, group_by)
    if keys is not None:
        active, fresh = active.reindex(keys, fill_value=0), fresh.reindex(keys, fill_value=0)
    return [
        NewVsReturningPoint(date=day_number_to_date(int(k)), new_customers=int(n), returning_customers=int(a) - int(n))
        for k, a, n in zip(active.index, active.to_numpy(), fresh.to_numpy(), strict=True)
    ]


# ----------------------------------------------------------------------------------------- finance
def finance(ctx: AnalyticsContext, sliced: Sliced) -> CapabilityAvailable[FinanceData] | CapabilityUnavailable:
    if not ctx.has_cost:
        return CapabilityUnavailable(reason=NO_COST)
    cur, prev = _totals_pair(sliced)
    category_margins: list[BreakdownItem] = []
    if not sliced.current.empty:
        margins = margins_by_category(sliced.current)
        total_profit = float(margins["profit"].sum())
        for name, margin, profit in zip(
            margins.index,
            margins["margin"].to_numpy(dtype="float64"),
            margins["profit"].to_numpy(dtype="float64"),
            strict=True,
        ):
            category_margins.append(
                BreakdownItem(
                    name=str(name),
                    value=float(to_fixed(float(margin), 1)),
                    share=round(float(profit) / total_profit * 100, 4) if total_profit else 0.0,
                    secondary=money(float(profit)),
                )
            )
        category_margins.sort(key=lambda m: -m.value)
    data = FinanceData(
        kpis=[
            _kpi(
                "revenue", "Revenue", cur.revenue, "currency", pct_change(cur.revenue, prev.revenue if prev else None)
            ),
            _kpi(
                "cost",
                "Total cost",
                cur.cost or 0,
                "currency",
                pct_change(cur.cost or 0, prev.cost if prev else None),
                inverse=True,
            ),
            *profit_kpis(cur, prev),
        ],
        trend=_series(ctx, sliced),
        category_margins=category_margins,
    )
    return CapabilityAvailable[FinanceData](data=data)
