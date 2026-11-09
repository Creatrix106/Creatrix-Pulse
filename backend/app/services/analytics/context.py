from dataclasses import dataclass
from datetime import date

from app.services.analytics.formatting import Formatters
from app.services.analytics.frames import AnalyticsFrame


@dataclass(frozen=True, slots=True)
class AnalyticsContext:
    """Everything the engine needs to know about one dataset besides the filters."""

    frame: AnalyticsFrame
    has_customers: bool
    has_cost: bool
    has_regions: bool
    formatters: Formatters

    @property
    def span(self) -> tuple[date, date]:
        return self.frame.min_date, self.frame.max_date
