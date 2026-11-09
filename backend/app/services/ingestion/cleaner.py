"""Raw table + column mapping → validated canonical rows.

Policy (deliberately strict, so analytics can be trusted):

* completely empty rows are ignored;
* every other row must have a readable date and a numeric revenue – otherwise the upload fails with a message
  that names the column, the number of bad rows and a few examples (nothing is silently dropped);
* optional numeric columns (quantity, cost) must be fully numeric when the *user* mapped them; when they were
  only *auto-detected* (Excel uploads) a bad column is ignored instead of failing the upload;
* blank text values get an explicit label ("Unknown product", "Uncategorized", "Unknown") so revenue never
  disappears from breakdowns; blank customers / order ids stay NULL (they cannot be invented).
"""

import math
import warnings
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from app.services.ingestion.errors import IngestionError
from app.services.ingestion.fields import FIELD_BY_ID
from app.services.ingestion.reader import ParsedTable

MIN_DATE = pd.Timestamp("1900-01-01")
MAX_DATE = pd.Timestamp("2100-12-31")
#: NUMERIC(18, 4) in PostgreSQL.
MAX_ABS_VALUE = 1e14

UNKNOWN_PRODUCT = "Unknown product"
UNCATEGORIZED = "Uncategorized"
UNKNOWN_REGION = "Unknown"

_ISO_DATE = r"^(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)"
_COMPACT_DATE = r"^(\d{4})(\d{2})(\d{2})$"
_NUMERIC_DATE = r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4}|\d{2})(?!\d)"
# 1,234.50 | 12,34,567.50 (Indian grouping) | 1234.5 | .5 | 1e5. A lone comma ("12,5", "1.234,56") is rejected on
# purpose: reading a decimal comma as a thousands separator would silently inflate values 10-1000x.
_NUMBER = r"[-+]?(?:(?:\d{1,3}(?:,\d{3})*|\d{1,2}(?:,\d{2})*,\d{3}|\d+)(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"


@dataclass(frozen=True, slots=True)
class Capabilities:
    customers: bool
    cost: bool
    regions: bool


@dataclass(slots=True)
class CleanedData:
    #: Columns: row_number, order_date, order_id, product, category, region, customer, quantity, revenue, cost
    #: sorted by (order_date, row_number).
    frame: pd.DataFrame
    #: Mapping actually used (a mapped column that turned out to be unusable is removed).
    mapping: dict[str, str]
    capabilities: Capabilities
    date_from: date
    date_to: date


# ------------------------------------------------------------------------------------- entry point
def clean_table(
    parsed: ParsedTable, mapping: dict[str, str], *, auto_mapped: bool, default_dayfirst: bool
) -> CleanedData:
    mapping = dict(mapping)
    raw = _blank_to_na(parsed.frame)
    keep = raw.notna().any(axis=1).to_numpy()
    row_numbers = parsed.row_numbers[keep]
    raw = raw.loc[keep].reset_index(drop=True)
    if raw.empty:
        raise IngestionError("The file has no data rows.")
    index = raw.index

    # ---- required fields -----------------------------------------------------------------------
    date_col = mapping["date"]
    dates = parse_dates(raw[date_col], dayfirst_default=default_dayfirst)
    bad = dates.isna()
    if bad.any():
        raise IngestionError(
            f"The date column “{date_col}” could not be read in {_rows(bad)} ({_examples(bad, row_numbers, raw[date_col])}). "
            "Use a standard format such as YYYY-MM-DD and upload the file again."
        )

    revenue = _numeric(raw, mapping["revenue"], "revenue", row_numbers)
    product = to_text(raw[mapping["product"]]).fillna(UNKNOWN_PRODUCT)

    # ---- optional numeric fields -----------------------------------------------------------------
    quantity = _optional_numeric(raw, mapping, "quantity", row_numbers, auto_mapped)
    cost = _optional_numeric(raw, mapping, "cost", row_numbers, auto_mapped)

    # ---- optional text fields ----------------------------------------------------------------------
    category = _optional_text(raw, mapping, "category")
    region = _optional_text(raw, mapping, "region")
    customer = _optional_text(raw, mapping, "customer")
    order_id = _optional_text(raw, mapping, "orderId")
    if category is not None:
        category = category.fillna(UNCATEGORIZED)
    if region is not None:
        region = region.fillna(UNKNOWN_REGION)

    def column(values: pd.Series | None, *, text: bool = True) -> pd.Series:
        if values is not None:
            return values
        return pd.Series(np.nan, index=index, dtype="str" if text else "float64")

    frame = pd.DataFrame(
        {
            "row_number": row_numbers.astype("int32"),
            "order_date": dates.astype("datetime64[us]"),
            "order_id": column(order_id),
            "product": product,
            "category": column(category),
            "region": column(region),
            "customer": column(customer),
            "quantity": quantity if quantity is not None else pd.Series(1.0, index=index),
            "revenue": revenue,
            "cost": column(cost, text=False),
        }
    ).sort_values(["order_date", "row_number"], kind="stable", ignore_index=True)

    return CleanedData(
        frame=frame,
        mapping=mapping,
        capabilities=Capabilities(customers=customer is not None, cost=cost is not None, regions=region is not None),
        date_from=frame["order_date"].iloc[0].date(),
        date_to=frame["order_date"].iloc[-1].date(),
    )


# --------------------------------------------------------------------------------- field helpers
def _numeric(raw: pd.DataFrame, column: str, label: str, row_numbers: np.ndarray) -> pd.Series:
    values = parse_numeric(raw[column])
    bad = values.isna() | (values.abs() >= MAX_ABS_VALUE)
    if bad.any():
        raise IngestionError(
            f"The {label} column “{column}” is empty, invalid or out of range in {_rows(bad)} "
            f"({_examples(bad, row_numbers, raw[column])}). Fix or remove those rows and upload the file again."
        )
    return values


def _optional_numeric(
    raw: pd.DataFrame, mapping: dict[str, str], field: str, row_numbers: np.ndarray, auto_mapped: bool
) -> pd.Series | None:
    column = mapping.get(field)
    if column is None:
        return None
    try:
        return _numeric(raw, column, FIELD_BY_ID[field].label.lower(), row_numbers)
    except IngestionError:
        if auto_mapped:  # the column was only a guess – do not fail the whole upload because of it
            del mapping[field]
            return None
        raise


def _optional_text(raw: pd.DataFrame, mapping: dict[str, str], field: str) -> pd.Series | None:
    column = mapping.get(field)
    if column is None:
        return None
    text = to_text(raw[column])
    if text.isna().all():  # mapped but completely empty: behave as if it was not mapped
        del mapping[field]
        return None
    return text


# ----------------------------------------------------------------------------------- text helpers
def _strip_blank(series: pd.Series) -> pd.Series:
    if isinstance(series.dtype, pd.StringDtype):
        text = series.str.strip()
        return text.mask(text == "")
    if series.dtype == object:
        return series.map(lambda v: (v.strip() or np.nan) if isinstance(v, str) else v)
    return series


def _blank_to_na(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({name: _strip_blank(frame[name]) for name in frame.columns}, index=frame.index)


def _scalar_text(value: object) -> str:
    if isinstance(value, float):
        return str(int(value)) if math.isfinite(value) and value == int(value) and abs(value) < 1e15 else repr(value)
    if isinstance(value, bool | np.bool_):
        return str(bool(value))
    if hasattr(value, "isoformat"):  # datetime.date / datetime.datetime / pandas.Timestamp
        return str(value.isoformat())
    return str(value)


def to_text(series: pd.Series) -> pd.Series:
    """Any column → trimmed pandas ``str`` values, blanks as NaN. Integer-valued floats lose their ``.0``
    (a numeric order id stored as 10001.0 by Excel must read "10001")."""
    if isinstance(series.dtype, pd.StringDtype):
        text = series
    elif pd.api.types.is_datetime64_any_dtype(series.dtype):
        text = series.map(lambda v: v.isoformat(), na_action="ignore").astype("str")
    else:
        text = series.map(_scalar_text, na_action="ignore").astype("str")
    text = text.str.strip()
    return text.mask(text == "")


# ----------------------------------------------------------------------------------------- numbers
def parse_numeric(series: pd.Series) -> pd.Series:
    """float64 values; NaN for blank, malformed, non-finite or boolean cells."""
    dtype = series.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return pd.Series(np.nan, index=series.index)
    if pd.api.types.is_numeric_dtype(dtype):
        values = series.astype("float64")
    else:
        text = to_text(series)
        negative = text.str.fullmatch(r"\(.*\)").fillna(False)  # accounting style: (50.00) = -50
        text = text.str.replace(r"^\((.*)\)$", r"\1", regex=True)
        text = text.str.replace(r"(?i)^(?:rs\.?|inr|usd|eur|gbp)\s*", "", regex=True)
        text = text.str.replace(r"[₹$€£¥\s]", "", regex=True)
        valid = text.str.fullmatch(_NUMBER).fillna(False)
        values = pd.to_numeric(text.where(valid).str.replace(",", "", regex=False), errors="coerce")
        values = values.astype("float64")  # to_numeric yields int64 when every value is integral
        values = values.where(~negative, -values)
    return values.where(np.isfinite(values))


# ------------------------------------------------------------------------------------------ dates
def parse_dates(series: pd.Series, *, dayfirst_default: bool = True) -> pd.Series:
    """datetime64[us] (midnight); NaT for blank, unreadable or implausible (outside 1900-2100) values.

    ISO dates are read by regex so that the *local calendar date written in the file* is kept even when a
    time zone offset follows it (pandas refuses mixed offsets). Ambiguous ``03/04/2026`` style dates are read
    day-first unless the column itself proves otherwise (e.g. a ``25/03/2026`` somewhere).
    """
    dtype = series.dtype
    if isinstance(dtype, pd.DatetimeTZDtype):
        series, dtype = series.dt.tz_localize(None), series.dt.tz_localize(None).dtype
    if pd.api.types.is_datetime64_any_dtype(dtype):
        result = series.dt.normalize()
    elif pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype):
        result = _numeric_dates(series, dayfirst_default)
    else:
        result = _text_dates(to_text(series), dayfirst_default)
    result = result.astype("datetime64[us]")
    plausible: pd.Series = result.where((result >= MIN_DATE) & (result <= MAX_DATE))
    return plausible


def _numeric_dates(series: pd.Series, dayfirst_default: bool) -> pd.Series:
    present = series.dropna()
    as_compact = (
        len(present) > 0
        and bool(((present >= 19000101) & (present <= 21001231)).all())
        and bool((present % 1 == 0).all())
    )
    if as_compact:  # 20260105 style integers
        return _text_dates(to_text(series), dayfirst_default)
    # Excel serial day numbers (1900 date system)
    return pd.to_datetime(series.astype("float64"), unit="D", origin="1899-12-30", errors="coerce").dt.normalize()


def _from_ymd(year: pd.Series, month: pd.Series, day: pd.Series) -> pd.Series:
    return pd.to_datetime({"year": year, "month": month, "day": day}, errors="coerce").astype("datetime64[us]")


def _digits(frame: pd.DataFrame) -> list[pd.Series]:
    return [pd.to_numeric(frame[i], errors="coerce") for i in range(frame.shape[1])]


def _infer_dayfirst(first: pd.Series, second: pd.Series, default: bool) -> bool:
    first_is_day, second_is_day = int((first > 12).sum()), int((second > 12).sum())
    if first_is_day != second_is_day:
        return first_is_day > second_is_day
    return default


def _text_dates(text: pd.Series, dayfirst_default: bool) -> pd.Series:
    # 1) ISO 8601 (optionally followed by a time and/or offset that we deliberately ignore)
    result = _from_ymd(*_digits(text.str.extract(_ISO_DATE)))

    # 2) compact 20260105
    todo = result.isna() & text.notna()
    if todo.any():
        result = result.fillna(_from_ymd(*_digits(text.where(todo).str.extract(_COMPACT_DATE))))

    # 3) 03/04/2026, 3-4-26, 03.04.2026
    todo = result.isna() & text.notna()
    if todo.any():
        first, second, year = _digits(text.where(todo).str.extract(_NUMERIC_DATE))
        dayfirst = _infer_dayfirst(first, second, dayfirst_default)
        day, month = (first, second) if dayfirst else (second, first)
        year = year.where(year >= 100, year + np.where(year < 69, 2000, 1900))  # POSIX two-digit-year pivot
        result = result.fillna(_from_ymd(year, month, day))

    # 4) everything else (5-Jan-2026, "Jan 5, 2026", 5 January 2026 …) one value at a time
    todo = result.isna() & text.notna()
    if todo.any():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # dateutil's day-first hints
            parsed = pd.to_datetime(text[todo], format="mixed", dayfirst=dayfirst_default, errors="coerce")
        result = result.fillna(parsed.reindex(result.index).astype("datetime64[us]"))
    return result


# --------------------------------------------------------------------------------- error messages
def _rows(mask: pd.Series) -> str:
    n = int(mask.sum())
    return f"{n:,} row{'' if n == 1 else 's'}"


def _examples(mask: pd.Series, row_numbers: np.ndarray, raw: pd.Series, limit: int = 3) -> str:
    parts: list[str] = []
    for position in np.flatnonzero(mask.to_numpy())[:limit]:
        value = raw.iloc[position]
        shown = "empty" if pd.isna(value) else f"“{str(value)[:30]}”"
        parts.append(f"row {row_numbers[position]}: {shown}")
    return "e.g. " + "; ".join(parts)
