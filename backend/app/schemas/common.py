"""Shared schema base. Field names are snake_case in Python and camelCase on the wire,
exactly matching the TypeScript types in the frontend (src/types/*.ts)."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

DatePreset = Literal["all", "last_30d", "last_90d", "last_180d", "ytd", "custom"]
ComparisonMode = Literal["none", "previous_period"]
GroupBy = Literal["day", "week", "month"]
MetricKey = Literal["revenue", "orders", "units", "aov", "cost", "profit"]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        from_attributes=True,
    )


def is_none(value: Any) -> bool:
    """``Field(exclude_if=is_none)``: omit optional TypeScript fields (`x?: T`) instead of sending null."""
    return value is None


class CapabilityAvailable[T](CamelModel):
    """`{ available: true, data }` – see ``Capability<T>`` in src/types/api.ts."""

    available: Literal[True] = True
    data: T


class CapabilityUnavailable(CamelModel):
    """`{ available: false, reason }` – the dataset lacks the columns this analysis needs."""

    available: Literal[False] = False
    reason: str
