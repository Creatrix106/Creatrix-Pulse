"""Bulk-load cleaned rows into ``sales_records`` with PostgreSQL ``COPY``.

COPY is an order of magnitude faster than batched INSERTs. It runs on its own short-lived connection (not the
shared pool) in a single transaction, so a failure part-way leaves no partial dataset behind.
"""

import uuid
from collections.abc import Awaitable, Callable, Iterator

import pandas as pd
import psycopg

COPY_SQL = (
    "COPY sales_records (dataset_id, row_number, order_date, order_id, product, category, region, customer, "
    "quantity, revenue, cost) FROM STDIN"
)

ProgressCallback = Callable[[int, int], Awaitable[None]]


def _nullable(series: pd.Series) -> list[object]:
    return series.astype(object).where(series.notna(), None).tolist()


def iter_rows(dataset_id: uuid.UUID, chunk: pd.DataFrame) -> Iterator[tuple[object, ...]]:
    columns = (
        [dataset_id] * len(chunk),
        chunk["row_number"].tolist(),
        chunk["order_date"].dt.date.tolist(),
        _nullable(chunk["order_id"]),
        _nullable(chunk["product"]),
        _nullable(chunk["category"]),
        _nullable(chunk["region"]),
        _nullable(chunk["customer"]),
        chunk["quantity"].round(4).tolist(),
        chunk["revenue"].round(4).tolist(),
        _nullable(chunk["cost"].round(4)),
    )
    return zip(*columns, strict=True)


async def copy_records(
    conninfo: str,
    dataset_id: uuid.UUID,
    frame: pd.DataFrame,
    *,
    chunk_rows: int,
    on_progress: ProgressCallback | None = None,
) -> None:
    total = len(frame)
    # `async with connection` commits on success and rolls back if anything raises.
    async with (
        await psycopg.AsyncConnection.connect(conninfo) as connection,
        connection.cursor() as cursor,
        cursor.copy(COPY_SQL) as copy,
    ):
        for start in range(0, total, chunk_rows):
            for row in iter_rows(dataset_id, frame.iloc[start : start + chunk_rows]):
                await copy.write_row(row)
            if on_progress is not None:
                await on_progress(min(start + chunk_rows, total), total)
