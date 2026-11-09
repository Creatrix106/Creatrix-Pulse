"""Raw-record browsing for the Data Explorer table."""

from typing import Any

from sqlalchemy import Float, Numeric, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset, SalesRecord
from app.schemas.analytics import ExplorerColumn, ExplorerData


def explorer_columns(dataset: Dataset) -> list[ExplorerColumn]:
    """Only columns the user actually provided: nothing is invented for fields they did not map."""
    mapped = dataset.mapping
    columns: list[ExplorerColumn] = []
    if "orderId" in mapped:
        columns.append(ExplorerColumn(key="orderId", label="Order ID", type="string"))
    columns += [
        ExplorerColumn(key="date", label="Date", type="date"),
        ExplorerColumn(key="product", label="Product", type="string"),
    ]
    if "category" in mapped:
        columns.append(ExplorerColumn(key="category", label="Category", type="string"))
    if dataset.has_regions:
        columns.append(ExplorerColumn(key="region", label="Region", type="string"))
    if dataset.has_customers:
        columns.append(ExplorerColumn(key="customerId", label="Customer", type="string"))
    if "quantity" in mapped:
        columns += [
            ExplorerColumn(key="quantity", label="Quantity", type="number"),
            ExplorerColumn(key="unitPrice", label="Unit price", type="number", format="currency"),
        ]
    columns.append(ExplorerColumn(key="revenue", label="Revenue", type="number", format="currency"))
    if dataset.has_cost:
        columns.append(ExplorerColumn(key="cost", label="Cost", type="number", format="currency"))
    return columns


def _source_columns() -> dict[str, object]:
    """Explorer key -> SQL expression. Dates are formatted and numbers cast in PostgreSQL, so Python gets
    ready-to-serialise str/float values instead of date/Decimal objects."""
    return {
        "orderId": SalesRecord.order_id,
        "date": func.to_char(SalesRecord.order_date, "YYYY-MM-DD"),
        "product": SalesRecord.product,
        "category": SalesRecord.category,
        "region": SalesRecord.region,
        "customerId": SalesRecord.customer,
        "quantity": cast(SalesRecord.quantity, Float(53)),
        "unitPrice": cast(
            func.round(cast(SalesRecord.revenue / func.nullif(SalesRecord.quantity, 0), Numeric), 4), Float(53)
        ),
        "revenue": cast(SalesRecord.revenue, Float(53)),
        "cost": cast(SalesRecord.cost, Float(53)),
    }


async def explorer_data(session: AsyncSession, dataset: Dataset, *, limit: int, offset: int) -> ExplorerData:
    """Newest records first (the table's default sort); ``limit``/``offset`` page through large datasets."""
    columns = explorer_columns(dataset)
    keys = [column.key for column in columns]
    available = _source_columns()
    result = await session.execute(
        select(*[available[key].label(key) for key in keys])  # type: ignore[attr-defined]
        .where(SalesRecord.dataset_id == dataset.id)
        .order_by(SalesRecord.order_date.desc(), SalesRecord.row_number)
        .limit(limit)
        .offset(offset)
    )
    records = result.all()
    values: dict[str, tuple[Any, ...]] = (
        dict(zip(keys, zip(*records, strict=True), strict=True)) if records else {key: () for key in keys}
    )
    if "quantity" in values:  # whole quantities print as 2, not 2.0
        values["quantity"] = tuple(int(q) if q.is_integer() else q for q in values["quantity"])
    rows: list[dict[str, str | int | float | None]] = [
        dict(zip(keys, row, strict=True)) for row in zip(*(values[key] for key in keys), strict=True)
    ]
    return ExplorerData(
        columns=columns,
        rows=rows,
        total=dataset.row_count,
        truncated=offset + len(rows) < dataset.row_count,
        limit=limit,
        offset=offset,
    )
