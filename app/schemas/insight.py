from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel, is_none

InsightType = Literal["positive", "negative", "anomaly", "observation", "recommendation"]


class InsightEvidence(CamelModel):
    label: str
    value: str


class Insight(CamelModel):
    id: str
    type: InsightType
    title: str
    summary: str
    metric: str | None = Field(None, exclude_if=is_none)
    evidence: list[InsightEvidence]
