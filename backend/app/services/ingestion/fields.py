"""Canonical business fields and header → field mapping.

Ported 1:1 from the frontend (src/config/files.ts and src/utils/dataset-profile.ts) so that the Excel path,
where the browser sends an empty mapping and the server detects the columns, picks exactly the columns the
CSV mapping step would have suggested.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.services.ingestion.errors import IngestionError


@dataclass(frozen=True, slots=True)
class FieldSpec:
    id: str
    label: str
    required: bool
    aliases: tuple[str, ...]


# Order matters: earlier fields claim a header first (see suggest_mapping).
CANONICAL_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "date",
        "Order date",
        True,
        ("date", "order date", "orderdate", "invoice date", "transaction date", "day", "created at"),
    ),
    FieldSpec("product", "Product", True, ("product", "product name", "item", "item name", "sku", "title")),
    FieldSpec(
        "revenue",
        "Revenue",
        True,
        ("revenue", "sales", "amount", "total", "total sales", "net sales", "order value", "line total"),
    ),
    FieldSpec("quantity", "Quantity", False, ("quantity", "qty", "units", "units sold")),
    FieldSpec(
        "orderId", "Order ID", False, ("order id", "orderid", "order no", "invoice", "invoice no", "transaction id")
    ),
    FieldSpec("category", "Category", False, ("category", "product category", "department", "type")),
    FieldSpec("region", "Region", False, ("region", "state", "zone", "area", "city", "location")),
    FieldSpec(
        "customer", "Customer", False, ("customer", "customer id", "customerid", "client", "buyer", "customer name")
    ),
    FieldSpec("cost", "Cost", False, ("cost", "cogs", "total cost", "expense", "unit cost")),
)

FIELD_BY_ID: dict[str, FieldSpec] = {f.id: f for f in CANONICAL_FIELDS}
REQUIRED_FIELDS: tuple[FieldSpec, ...] = tuple(f for f in CANONICAL_FIELDS if f.required)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _join_labels(labels: Sequence[str]) -> str:
    """["a", "b", "c"] → "a, b and c" """
    return labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]


def normalise_header(header: str) -> str:
    """``header.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()``"""
    return _NON_ALNUM.sub(" ", header.lower()).strip()


def suggest_mapping(headers: Sequence[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for field in CANONICAL_FIELDS:
        for header in headers:
            if header not in used and normalise_header(header) in field.aliases:
                mapping[field.id] = header
                used.add(header)
                break
    return mapping


def resolve_mapping(headers: Sequence[str], provided: dict[str, str] | None) -> dict[str, str]:
    """Effective mapping for a file.

    * empty / missing → detect from the headers (always the case for Excel uploads);
    * given → used exactly as chosen by the user (an unmapped optional field stays unmapped), after
      checking that every mapped column exists and no column feeds two fields.
    """
    if not provided:
        mapping = suggest_mapping(headers)
        missing = [f for f in REQUIRED_FIELDS if f.id not in mapping]
        if missing:
            names = _join_labels([f"“{f.label}”" for f in missing])
            raise IngestionError(
                f"We couldn't find a column for {names}. Rename the column headers (for example “Date”, "
                "“Product”, “Revenue”) or upload a CSV so you can map the columns manually."
            )
        return mapping

    by_exact = {h: h for h in headers}
    by_loose = {h.strip().casefold(): h for h in headers}
    resolved: dict[str, str] = {}
    for field_id, column in provided.items():
        wanted = column.strip()
        actual = by_exact.get(wanted) or by_loose.get(wanted.casefold())
        if actual is None:
            raise IngestionError(
                f"The column “{wanted}” you mapped to “{FIELD_BY_ID[field_id].label}” isn't in the file."
            )
        resolved[field_id] = actual

    for field in REQUIRED_FIELDS:
        if field.id not in resolved:
            raise IngestionError(f"Map a column to “{field.label}” – it is required to generate analytics.")

    seen: dict[str, str] = {}
    for field_id, column in resolved.items():
        if column in seen:
            raise IngestionError(
                f"The column “{column}” is mapped to both “{FIELD_BY_ID[seen[column]].label}” and "
                f"“{FIELD_BY_ID[field_id].label}”. Each field needs its own column."
            )
        seen[column] = field_id
    return resolved
