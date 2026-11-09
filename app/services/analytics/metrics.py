"""Vectorised aggregations over (slices of) an analytics frame. Pure functions: no I/O, no mutation."""

import hashlib
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from app.schemas.analytics import BreakdownItem, ProductPerformance, TimeSeriesPoint
from app.services.analytics.formatting import js_round, to_fixed

#: A zero-filled series is skipped beyond this many buckets (e.g. a daily chart over a century).
MAX_FILLED_BUCKETS = 10_000
UNCATEGORIZED = "Uncategorized"


def money(value: float) -> float:
    return round(float(value), 2)


def ratio(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def pct_change(current: float, previous: float | None) -> float | None:
    """% change vs the previous value; None when there is nothing (or zero) to compare with."""
    if previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100


# ---------------------------------------------------------------------------------------- totals
@dataclass(frozen=True, slots=True)
class Totals:
    revenue: float
    orders: int
    units: float
    aov: float
    cost: float | None
    profit: float | None
    margin: float | None  # percent


def totals(df: pd.DataFrame) -> Totals:
    revenue = float(df["revenue"].sum())
    orders = int(df["order_code"].nunique())
    # Profit exists only when *every* row has a cost – never computed from partial cost data.
    has_cost = len(df) > 0 and bool(df["cost"].notna().all())
    cost = float(df["cost"].sum()) if has_cost else None
    profit = None if cost is None else revenue - cost
    return Totals(
        revenue=revenue,
        orders=orders,
        units=float(df["quantity"].sum()),
        aov=revenue / orders if orders else 0.0,
        cost=cost,
        profit=profit,
        margin=None if profit is None or revenue == 0 else profit / revenue * 100,
    )


# ---------------------------------------------------------------------------------------- buckets
def bucket_days(dates: np.ndarray, group_by: str) -> np.ndarray:
    """Start of the day/week/month bucket of every date, as int64 days since 1970-01-01.

    Weeks start on Monday (1970-01-01 was a Thursday, so a day's Monday-based weekday is (n + 3) mod 7).
    """
    days = dates.astype("datetime64[D]")
    if group_by == "day":
        result = days.astype("int64")
    elif group_by == "month":
        result = days.astype("datetime64[M]").astype("datetime64[D]").astype("int64")
    else:
        n = days.astype("int64")
        result = n - (n + 3) % 7
    return np.asarray(result, dtype="int64")


def bucket_range(start: date, end: date, group_by: str) -> np.ndarray:
    """Every bucket start (int64 days) that overlaps [start, end]."""
    first = np.datetime64(start, "D")
    last = np.datetime64(end, "D")
    if group_by == "day":
        return np.arange(first, last + np.timedelta64(1, "D")).astype("int64")
    if group_by == "month":
        months = np.arange(first.astype("datetime64[M]"), last.astype("datetime64[M]") + np.timedelta64(1, "M"))
        return months.astype("datetime64[D]").astype("int64")
    lo = bucket_days(np.array([first]), "week")[0]
    hi = bucket_days(np.array([last]), "week")[0]
    return np.arange(lo, hi + 1, 7, dtype="int64")


def day_number_to_date(n: int) -> date:
    return np.datetime64(int(n), "D").astype(object)  # type: ignore[no-any-return]


def fill_keys(
    window: tuple[date, date] | None, span: tuple[date, date], group_by: str, *, clamp_start: bool = True
) -> np.ndarray | None:
    """Buckets to zero-fill: the window clamped to the dataset's own date span.

    ``clamp_start=False`` is used for the *previous-period* series: the UI overlays it on the current series
    position by position, so buckets before the dataset began must stay in the series (as zeros, exactly how
    the previous-period KPI totals already treat uncovered days) or every later point would shift left.
    """
    if window is None:
        return None
    start = max(window[0], span[0]) if clamp_start else window[0]
    end = min(window[1], span[1])
    if start > end:
        return np.empty(0, dtype="int64")
    keys = bucket_range(start, end, group_by)
    return keys if len(keys) <= MAX_FILLED_BUCKETS else None


# ------------------------------------------------------------------------------------ time series
def time_series(
    df: pd.DataFrame, group_by: str, *, fill: np.ndarray | None = None, has_cost: bool = False
) -> list[TimeSeriesPoint]:
    """One point per bucket. With ``fill`` (see :func:`fill_keys`) buckets without sales appear as zeros, so
    that charts show real dips and the "previous period" overlay lines up position by position."""
    if df.empty:
        return []
    work = pd.DataFrame(
        {
            "k": bucket_days(df["date"].to_numpy(), group_by),
            "revenue": df["revenue"].to_numpy(),
            "units": df["quantity"].to_numpy(),
            "order": df["order_code"].to_numpy(),
        }
    )
    if has_cost:
        work["cost"] = df["cost"].to_numpy()
    grouped = work.groupby("k", sort=True)
    agg = pd.DataFrame(
        {"revenue": grouped["revenue"].sum(), "units": grouped["units"].sum(), "orders": grouped["order"].nunique()}
    )
    if has_cost:
        agg["cost"] = grouped["cost"].sum()
    if fill is not None:
        agg = agg.reindex(fill, fill_value=0)

    keys = agg.index.to_numpy()
    revenues = agg["revenue"].to_numpy(dtype="float64")
    orders = agg["orders"].to_numpy(dtype="int64")
    units = agg["units"].to_numpy(dtype="float64")
    costs = agg["cost"].to_numpy(dtype="float64") if has_cost else None

    points: list[TimeSeriesPoint] = []
    for i in range(len(keys)):
        revenue, n_orders = float(revenues[i]), int(orders[i])
        point = TimeSeriesPoint(
            date=day_number_to_date(int(keys[i])),
            revenue=money(revenue),
            orders=n_orders,
            units=round(float(units[i]), 4),
            aov=js_round(revenue / n_orders) if n_orders else 0,
        )
        if costs is not None:
            cost = float(costs[i])
            point.cost, point.profit = money(cost), money(revenue - cost)
            if revenue != 0:
                point.margin = float(to_fixed((revenue - cost) / revenue * 100, 1))
        points.append(point)
    return points


# -------------------------------------------------------------------------------------- breakdown
def _sum_by(df: pd.DataFrame, column: str) -> pd.DataFrame:
    grouped = df.groupby(column, observed=True)[["revenue", "quantity"]].sum()
    grouped.index = grouped.index.astype(object)
    return grouped


def breakdown(df: pd.DataFrame, column: str, previous: pd.DataFrame | None) -> list[BreakdownItem]:
    """Revenue by a dimension (category/region), largest first. Rows without a value are left out."""
    current = _sum_by(df, column)
    if current.empty:
        return []
    prior = _sum_by(previous, column)["revenue"].to_dict() if previous is not None else None
    total = float(current["revenue"].sum())
    current = current.sort_values("revenue", ascending=False, kind="stable")
    names = [str(name) for name in current.index]
    revenues = current["revenue"].to_numpy(dtype="float64")
    units = current["quantity"].to_numpy(dtype="float64")
    items: list[BreakdownItem] = []
    for name, revenue, unit_count in zip(names, revenues, units, strict=True):
        revenue = float(revenue)
        before = prior.get(name) if prior is not None else None
        items.append(
            BreakdownItem(
                name=name,
                value=money(revenue),
                share=round(revenue / total * 100, 4) if total else 0.0,
                secondary=round(float(unit_count), 4),
                change=ratio(pct_change(revenue, float(before) if before is not None else None)),
            )
        )
    return items


# --------------------------------------------------------------------------------------- products
def product_id(name: str) -> str:
    """Stable id derived from the product name (the file has no product-id column)."""
    return "p-" + hashlib.blake2s(name.encode(), digest_size=5).hexdigest()


def _group_products(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("product", observed=True)
    out = pd.DataFrame(
        {
            "revenue": grouped["revenue"].sum(),
            "units": grouped["quantity"].sum(),
            "orders": grouped["order_code"].nunique(),
            "cost": grouped["cost"].sum(),
            "category": grouped["category"].first(),
        }
    )
    out.index = out.index.astype(object)
    return out


def product_performance(df: pd.DataFrame, previous: pd.DataFrame | None, *, has_cost: bool) -> list[ProductPerformance]:
    """Per-product metrics, best revenue first."""
    current = _group_products(df)
    if current.empty:
        return []
    prior = _group_products(previous)["revenue"].to_dict() if previous is not None else None
    total = float(current["revenue"].sum())
    current = current.sort_values("revenue", ascending=False, kind="stable")
    names = [str(name) for name in current.index]
    revenues = current["revenue"].to_numpy(dtype="float64")
    units = current["units"].to_numpy(dtype="float64")
    orders = current["orders"].to_numpy(dtype="int64")
    costs = current["cost"].to_numpy(dtype="float64")
    categories = current["category"].astype(object).to_numpy()
    products: list[ProductPerformance] = []
    for i, name in enumerate(names):
        revenue = float(revenues[i])
        before = prior.get(name) if prior is not None else None
        category = categories[i]
        products.append(
            ProductPerformance(
                id=product_id(name),
                name=name,
                category=UNCATEGORIZED if pd.isna(category) else str(category),
                revenue=money(revenue),
                units=round(float(units[i]), 4),
                orders=int(orders[i]),
                share=round(revenue / total * 100, 4) if total else 0.0,
                change=ratio(pct_change(revenue, float(before) if before is not None else None)),
                margin=ratio((revenue - float(costs[i])) / revenue * 100) if has_cost and revenue else None,
            )
        )
    return products


def margins_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Columns: revenue, cost, profit, margin (percent). Index: category."""
    grouped = df.groupby("category", observed=True)[["revenue", "cost"]].sum()
    grouped.index = grouped.index.astype(object)
    grouped["profit"] = grouped["revenue"] - grouped["cost"]
    grouped["margin"] = np.where(
        grouped["revenue"] != 0, grouped["profit"] / grouped["revenue"].where(grouped["revenue"] != 0, 1) * 100, 0.0
    )
    return grouped
