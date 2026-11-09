"""Dataset metadata computed once at ingestion: column types and filter options.

Column types follow the exact rules of the browser profiler (src/utils/dataset-profile.ts: a type wins when
more than 90% of the non-empty values match), so the "Columns" metadata the user saw during mapping and the
one stored by the server agree.
"""

from typing import Any

import pandas as pd

from app.services.ingestion.cleaner import to_text
from app.services.ingestion.reader import ParsedTable

MAX_FILTER_OPTIONS = 500

_DATE = r"^\d{4}-\d{1,2}-\d{1,2}(?:[T ].*)?$|^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$"
_NUMBER = r"^[-+]?[₹$€£]?\s?[\d,]*\.?\d+$"
_BOOLEAN = r"(?i)^(?:true|false|yes|no)$"


def infer_type(series: pd.Series) -> str:
    dtype = series.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "date"
    if pd.api.types.is_numeric_dtype(dtype):
        return "number"
    values = to_text(series).dropna()
    if values.empty:
        return "string"
    for name, pattern in (("date", _DATE), ("number", _NUMBER), ("boolean", _BOOLEAN)):
        if values.str.match(pattern).mean() > 0.9:
            return name
    return "string"


def build_columns(parsed: ParsedTable, mapping: dict[str, str]) -> list[dict[str, Any]]:
    """One entry per column of the uploaded file (mapped or not), in file order."""
    mapped_to = {column: field for field, column in mapping.items()}
    columns: list[dict[str, Any]] = []
    for name in parsed.frame.columns:
        entry: dict[str, Any] = {"name": name, "type": infer_type(parsed.frame[name])}
        if name in mapped_to:
            entry["mappedTo"] = mapped_to[name]
        columns.append(entry)
    return columns


def build_filter_options(frame: pd.DataFrame) -> dict[str, list[str]]:
    def distinct(column: str) -> list[str]:
        return sorted(frame[column].dropna().unique().tolist())[:MAX_FILTER_OPTIONS]

    return {"categories": distinct("category"), "regions": distinct("region")}
