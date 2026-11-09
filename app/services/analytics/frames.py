"""The in-memory analytics frame of a dataset: loading, normalising and caching.

PostgreSQL is the system of record; pandas is the analytics engine. A dataset's rows are loaded once into a
compact DataFrame (categorical dimensions, factorised order ids) and kept in a small LRU cache, so switching
filters on the dashboard is pure in-memory work. Datasets are immutable once ``ready`` and ids are never
reused, so a cached frame can never be stale; deleting a dataset only frees memory.
"""

import asyncio
import uuid
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

import pandas as pd
from sqlalchemy import Float, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import SalesRecord

_LOAD_COLUMNS = (
    "row_number",
    "order_date",
    "order_id",
    "product",
    "category",
    "region",
    "customer",
    "quantity",
    "revenue",
    "cost",
)


@dataclass(frozen=True, slots=True)
class AnalyticsFrame:
    #: Columns: date (datetime64[us], sorted), order_code (int32), product/category/region/customer
    #: (category dtype, NaN = unknown), quantity/revenue/cost (float64, cost NaN when absent).
    df: pd.DataFrame
    min_date: date
    max_date: date
    has_cost: bool
    has_category: bool
    has_region: bool
    has_customer: bool

    @property
    def nbytes(self) -> int:
        return int(self.df.memory_usage(deep=True).sum())


def build_frame(rows: pd.DataFrame) -> AnalyticsFrame:
    """Normalise rows (as cleaned at ingestion, or as loaded from PostgreSQL) into the analytics layout."""
    rows = rows.reset_index(drop=True)
    order_id = rows["order_id"].astype("str")
    # A row without an order id is its own order.
    order_key = order_id.where(order_id.notna(), "\x00" + rows["row_number"].astype("str"))
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(rows["order_date"]).astype("datetime64[us]"),
            "order_code": pd.factorize(order_key)[0].astype("int32"),
            "product": rows["product"].astype("str").astype("category"),
            "category": rows["category"].astype("str").astype("category"),
            "region": rows["region"].astype("str").astype("category"),
            "customer": rows["customer"].astype("str").astype("category"),
            "quantity": pd.to_numeric(rows["quantity"], errors="coerce").astype("float64"),
            "revenue": pd.to_numeric(rows["revenue"], errors="coerce").astype("float64"),
            "cost": pd.to_numeric(rows["cost"], errors="coerce").astype("float64"),
        }
    )
    if not df["date"].is_monotonic_increasing:
        df = df.sort_values("date", kind="stable", ignore_index=True)
    if df.empty:
        raise ValueError("A dataset frame cannot be empty.")
    return AnalyticsFrame(
        df=df,
        min_date=df["date"].iloc[0].date(),
        max_date=df["date"].iloc[-1].date(),
        has_cost=bool(df["cost"].notna().any()),
        has_category=bool(df["category"].notna().any()),
        has_region=bool(df["region"].notna().any()),
        has_customer=bool(df["customer"].notna().any()),
    )


async def load_frame(session: AsyncSession, dataset_id: uuid.UUID) -> AnalyticsFrame:
    stmt = (
        select(
            SalesRecord.row_number,
            SalesRecord.order_date,
            SalesRecord.order_id,
            SalesRecord.product,
            SalesRecord.category,
            SalesRecord.region,
            SalesRecord.customer,
            cast(SalesRecord.quantity, Float(53)).label("quantity"),
            cast(SalesRecord.revenue, Float(53)).label("revenue"),
            cast(SalesRecord.cost, Float(53)).label("cost"),
        )
        .where(SalesRecord.dataset_id == dataset_id)
        .order_by(SalesRecord.order_date, SalesRecord.row_number)
    )
    records = (await session.execute(stmt)).all()

    def to_frame() -> AnalyticsFrame:
        # zip(*rows) + one Series per column is ~3x faster than DataFrame.from_records over Row objects.
        columns = list(zip(*records, strict=True)) if records else [()] * len(_LOAD_COLUMNS)
        return build_frame(
            pd.DataFrame({name: pd.Series(values) for name, values in zip(_LOAD_COLUMNS, columns, strict=True)})
        )

    return await asyncio.to_thread(to_frame)


class FrameCache:
    """Byte- and count-bounded LRU with single-flight loading (concurrent requests share one DB read)."""

    def __init__(self, max_items: int, max_bytes: int) -> None:
        self.max_items, self.max_bytes = max_items, max_bytes
        self._items: OrderedDict[uuid.UUID, AnalyticsFrame] = OrderedDict()
        self._locks: dict[uuid.UUID, asyncio.Lock] = {}

    def get(self, key: uuid.UUID) -> AnalyticsFrame | None:
        frame = self._items.get(key)
        if frame is not None:
            self._items.move_to_end(key)
        return frame

    def put(self, key: uuid.UUID, frame: AnalyticsFrame) -> None:
        self._items[key] = frame
        self._items.move_to_end(key)
        while len(self._items) > 1 and (
            len(self._items) > self.max_items or sum(f.nbytes for f in self._items.values()) > self.max_bytes
        ):
            self._items.popitem(last=False)

    def evict(self, key: uuid.UUID) -> None:
        self._items.pop(key, None)

    def clear(self) -> None:
        self._items.clear()
        self._locks.clear()

    async def get_or_load(self, key: uuid.UUID, loader: Callable[[], Awaitable[AnalyticsFrame]]) -> AnalyticsFrame:
        cached = self.get(key)
        if cached is not None:
            return cached
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self.get(key)  # another request may have loaded it while we waited
            if cached is None:
                cached = await loader()
                self.put(key, cached)
        self._locks.pop(key, None)
        return cached

    def __len__(self) -> int:
        return len(self._items)


@lru_cache
def get_frame_cache() -> FrameCache:
    settings = get_settings()
    return FrameCache(settings.analytics_cache_max_datasets, settings.analytics_cache_max_mb * 1024 * 1024)
