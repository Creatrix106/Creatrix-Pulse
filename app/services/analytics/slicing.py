"""Filter semantics of the dashboard: date presets, previous-period comparison, category/region scope.

Ported from ``sliceRows`` in the frontend mock (src/services/mock/engine.ts) so that real data behaves
exactly like the demo data did:

* presets are relative to the *latest date in the dataset*, not to today (uploads are historical files);
* the comparison window is the immediately preceding period of equal length; it is ignored for "all time";
* ``scoped`` = rows matching the category/region filters regardless of date (customer "first seen" needs it).
"""

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.services.analytics.frames import AnalyticsFrame

PRESET_DAYS = {"last_30d": 30, "last_90d": 90, "last_180d": 180}


@dataclass(frozen=True, slots=True)
class AnalyticsFilters:
    date_preset: str = "all"
    date_from: date | None = None
    date_to: date | None = None
    comparison: str = "none"
    group_by: str = "month"
    categories: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()


@dataclass(slots=True)
class Sliced:
    frame: AnalyticsFrame
    filters: AnalyticsFilters
    current: pd.DataFrame
    previous: pd.DataFrame | None
    range_from: date
    range_to: date

    @property
    def previous_range(self) -> tuple[date, date] | None:
        if self.previous is None:
            return None
        return _previous_window(self.range_from, self.range_to)

    def scoped(self) -> pd.DataFrame:
        """Every row matching the category/region filters, whatever its date."""
        return _scope(self.frame.df, self.filters)


def _previous_window(start: date, end: date) -> tuple[date, date]:
    length = (end - start).days + 1
    return start - timedelta(days=length), start - timedelta(days=1)


def _scope(df: pd.DataFrame, filters: AnalyticsFilters) -> pd.DataFrame:
    if filters.categories:
        df = df[df["category"].isin(filters.categories)]
    if filters.regions:
        df = df[df["region"].isin(filters.regions)]
    return df


def _window(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Rows with start <= date <= end. The frame is sorted by date, so this is two binary searches + a view."""
    dates = df["date"].to_numpy()
    lo = int(dates.searchsorted(np.datetime64(start, "us"), side="left"))
    hi = int(dates.searchsorted(np.datetime64(end, "us"), side="right"))
    return df.iloc[lo:hi]


def resolve_range(frame: AnalyticsFrame, filters: AnalyticsFilters) -> tuple[date, date]:
    start, end = frame.min_date, frame.max_date
    days = PRESET_DAYS.get(filters.date_preset)
    if days:
        start = frame.max_date - timedelta(days=days - 1)
    elif filters.date_preset == "ytd":
        start = date(frame.max_date.year, 1, 1)
    elif filters.date_preset == "custom" and filters.date_from and filters.date_to:
        start, end = filters.date_from, filters.date_to
    return start, end


def slice_frame(frame: AnalyticsFrame, filters: AnalyticsFilters) -> Sliced:
    start, end = resolve_range(frame, filters)
    current = _scope(_window(frame.df, start, end), filters)

    previous: pd.DataFrame | None = None
    if filters.comparison == "previous_period" and filters.date_preset != "all":
        prev_start, prev_end = _previous_window(start, end)
        candidate = _scope(_window(frame.df, prev_start, prev_end), filters)
        previous = candidate if len(candidate) else None
    return Sliced(frame=frame, filters=filters, current=current, previous=previous, range_from=start, range_to=end)
