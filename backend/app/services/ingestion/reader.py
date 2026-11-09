"""Bytes → DataFrame for the three accepted formats (.csv, .xlsx, .xls).

* CSV is read as *text only* (``dtype=str``) so the cleaner decides how every value is interpreted, and only
  genuinely empty cells become missing values. (pandas' default NA list would turn a region called "NA" –
  North America – or a product called "N/A" into NaN.)
* Excel is read with the Rust ``calamine`` engine, which handles .xlsx *and* the legacy .xls format without
  xlrd/openpyxl, and returns typed cells (dates, numbers, text).
"""

import io
import logging
import re
import warnings
import zipfile
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from app.services.ingestion.errors import IngestionError

log = logging.getLogger(__name__)

FileKind = Literal["csv", "excel"]

_ZIP_MAGIC = b"PK\x03\x04"
_OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
_UNNAMED = re.compile(r"Unnamed: \d+(_level_\d+)?")
_QUOTED = re.compile(r'"[^"]*"')
_DELIMITERS = (",", ";", "\t", "|")


@dataclass(slots=True)
class ParsedTable:
    kind: FileKind
    frame: pd.DataFrame
    #: Spreadsheet row number (header = row 1) of every frame row, for error messages.
    row_numbers: np.ndarray


def file_kind(filename: str) -> FileKind | None:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith((".xlsx", ".xls")):
        return "excel"
    return None


def read_table(
    data: bytes, filename: str, *, max_rows: int, max_columns: int, max_uncompressed_bytes: int
) -> ParsedTable:
    kind = file_kind(filename)
    if kind is None:
        raise IngestionError("Unsupported file type. Upload a .csv, .xlsx or .xls file.")
    if not data:
        raise IngestionError("The file is empty.")

    if kind == "csv":
        _reject_binary_masquerading_as_csv(data)
        frame = _read_csv(data, max_rows)
    else:
        frame = _read_excel(data, filename, max_rows, max_uncompressed_bytes)

    if len(frame.columns) > max_columns:
        raise IngestionError(f"The file has {len(frame.columns):,} columns; the limit is {max_columns:,}.")
    if len(frame) > max_rows:
        raise IngestionError(f"The file has more than {max_rows:,} rows, which is the limit for one dataset.")

    frame.columns = _clean_headers(frame.columns)
    return ParsedTable(kind=kind, frame=frame, row_numbers=np.arange(2, len(frame) + 2))


# --------------------------------------------------------------------------------------------- CSV
def _reject_binary_masquerading_as_csv(data: bytes) -> None:
    if data.startswith(_ZIP_MAGIC):
        raise IngestionError(
            "This file is an Excel/zip archive with a .csv extension. Save it as a real CSV, or upload it as .xlsx."
        )
    if data.startswith(_OLE_MAGIC):
        raise IngestionError(
            "This file is a legacy Excel workbook with a .csv extension. Upload it as .xls or export it to CSV."
        )
    if b"\x00" in data[:8192]:
        raise IngestionError("This doesn't look like a text CSV file (it contains binary data).")


def _decode(data: bytes) -> str:
    # utf-8-sig drops a BOM; cp1252 is what Excel on Windows writes for "CSV"; latin-1 can never fail.
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _sniff_delimiter(text: str) -> str:
    first_line = next((line for line in text.splitlines()[:20] if line.strip()), "")
    header = _QUOTED.sub("", first_line)  # commas inside quoted header names must not count
    counts = {d: header.count(d) for d in _DELIMITERS}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 0 else ","


def _read_csv(data: bytes, max_rows: int) -> pd.DataFrame:
    text = _decode(data)
    try:
        # Two traps in pandas' defaults, both of which would silently corrupt data:
        #  * a row with MORE fields than the header makes pandas use the first field as an implicit *index*,
        #    shifting every column by one -> index_col=False;
        #  * with index_col=False, surplus non-empty fields are dropped with only a ParserWarning
        #    ("loss of data") -> that warning is promoted to an error here. (A trailing comma on every row,
        #    a common export quirk, is still accepted: its surplus field is empty.)
        with warnings.catch_warnings():
            warnings.simplefilter("error", pd.errors.ParserWarning)
            return pd.read_csv(
                io.StringIO(text),
                sep=_sniff_delimiter(text),
                dtype=str,
                keep_default_na=False,
                na_values=[""],
                index_col=False,
                on_bad_lines="error",
                low_memory=False,
                nrows=max_rows + 1,  # one extra row is enough to detect "too many rows" without loading everything
            )
    except pd.errors.EmptyDataError:
        raise IngestionError("The file is empty.") from None
    except (pd.errors.ParserError, pd.errors.ParserWarning) as exc:
        line = re.search(r"line (\d+)", str(exc))
        where = f"Line {line.group(1)}" if line else "Some rows"
        raise IngestionError(
            f"{where} {'has' if line else 'have'} more values than the header row. "
            "Check for an unquoted comma inside a value or a missing column header."
        ) from None


# ------------------------------------------------------------------------------------------- Excel
def _read_excel(data: bytes, filename: str, max_rows: int, max_uncompressed_bytes: int) -> pd.DataFrame:
    if filename.lower().endswith(".xlsx"):
        _guard_xlsx(data, max_uncompressed_bytes)
    elif not data.startswith(_OLE_MAGIC):
        raise IngestionError(
            "This file has an .xls extension but isn't an Excel workbook. Re-save it from Excel or export to CSV."
        )

    try:
        with pd.ExcelFile(io.BytesIO(data), engine="calamine") as workbook:
            names = workbook.sheet_names
            for name in names:  # use the first sheet that actually holds data
                frame = pd.read_excel(
                    workbook, sheet_name=name, header=0, keep_default_na=False, na_values=[""], nrows=max_rows + 1
                )
                if len(frame.columns) > 0:
                    return frame
    except IngestionError:
        raise
    except Exception:  # calamine/pandas raise many different types for corrupt or protected files
        log.warning("Could not read workbook %r", filename, exc_info=True)
        raise IngestionError(
            "We couldn't read this Excel file. It may be corrupted or password-protected. "
            "Re-save it as .xlsx or export it to CSV and try again."
        ) from None
    raise IngestionError("The workbook has no data.")


def _guard_xlsx(data: bytes, max_uncompressed_bytes: int) -> None:
    """An .xlsx is a zip: refuse archives that would inflate far beyond the upload limit (zip bombs)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            inflated = sum(info.file_size for info in archive.infolist())
    except zipfile.BadZipFile:
        raise IngestionError("This .xlsx file is corrupted or isn't a real Excel workbook.") from None
    if inflated > max_uncompressed_bytes:
        raise IngestionError(
            "This workbook contains more data than we can process. Export the sheet you need to CSV instead."
        )


# ----------------------------------------------------------------------------------------- headers
def _clean_headers(columns: pd.Index) -> list[str]:
    """Same rule as the browser (``h.trim() || "Column N"``), plus de-duplication."""
    names: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(columns):
        name = str(raw).strip()
        if not name or _UNNAMED.fullmatch(name):
            name = f"Column {index + 1}"
        base, counter = name, 2
        while name in seen:
            name, counter = f"{base} ({counter})", counter + 1
        seen.add(name)
        names.append(name)
    return names
