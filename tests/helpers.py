"""Helpers shared by API tests."""

import io

import httpx

from tests.factories import make_rows

FULL_MAPPING = {
    "date": "Order Date",
    "orderId": "Order ID",
    "product": "Product",
    "category": "Category",
    "region": "Region",
    "customer": "Customer ID",
    "quantity": "Quantity",
    "revenue": "Revenue",
    "cost": "Cost",
}


def sales_csv(days: int = 120, seed: int = 3, **shape) -> bytes:
    """A realistic CSV in the shape users upload (display column names, ISO dates)."""
    rows = make_rows(days=days, seed=seed, **shape)
    frame = rows.rename(
        columns={
            "order_date": "Order Date",
            "order_id": "Order ID",
            "product": "Product",
            "category": "Category",
            "region": "Region",
            "customer": "Customer ID",
            "quantity": "Quantity",
            "revenue": "Revenue",
            "cost": "Cost",
        }
    ).drop(columns=["row_number"])
    frame["Order Date"] = frame["Order Date"].dt.strftime("%Y-%m-%d")
    frame = frame.dropna(axis=1, how="all")
    frame = frame.replace("nan", "")
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode()


async def upload(
    client: httpx.AsyncClient,
    data: bytes,
    name: str = "sales.csv",
    mapping: dict | None = None,
    replace: str | None = None,
    content_type: str = "text/csv",
) -> httpx.Response:
    import json

    form: dict[str, str] = {"mapping": json.dumps(mapping if mapping is not None else {})}
    if replace:
        form["replaceDatasetId"] = replace
    return await client.post("/api/datasets", files={"file": (name, data, content_type)}, data=form)


async def upload_and_wait(client: httpx.AsyncClient, data: bytes, name: str = "sales.csv", **kwargs) -> dict:
    """Upload, wait for the background job, and return the final dataset JSON."""
    from app.services.jobs import jobs

    response = await upload(client, data, name, **kwargs)
    assert response.status_code == 202, response.text
    dataset_id = response.json()["datasetId"]
    await jobs.wait_idle(timeout=60)
    final = await client.get(f"/api/datasets/{dataset_id}")
    assert final.status_code == 200, final.text
    return final.json()


# ------------------------------------------------------------------------------------ Excel files
def display_frame(**shape):
    """make_rows() in the column naming users have in their files."""
    import pandas as pd

    rows = make_rows(**shape).drop(columns=["row_number"])
    frame = rows.rename(
        columns={
            "order_date": "Order Date",
            "order_id": "Order ID",
            "product": "Product",
            "category": "Category",
            "region": "Region",
            "customer": "Customer ID",
            "quantity": "Quantity",
            "revenue": "Revenue",
            "cost": "Cost",
        }
    )
    return pd.DataFrame(frame)


def to_xlsx(frame) -> bytes:
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False, engine="openpyxl")  # dates become real Excel date cells
    return buffer.getvalue()


def to_xls(frame) -> bytes:
    """Legacy BIFF .xls (pandas can no longer write it; xlwt is used directly)."""
    import xlwt

    book = xlwt.Workbook()
    sheet = book.add_sheet("Sales")
    date_style = xlwt.easyxf(num_format_str="YYYY-MM-DD")
    for col, name in enumerate(frame.columns):
        sheet.write(0, col, name)
    for row_idx, row in enumerate(frame.itertuples(index=False), start=1):
        for col, value in enumerate(row):
            if hasattr(value, "to_pydatetime"):
                sheet.write(row_idx, col, value.to_pydatetime(), date_style)
            elif isinstance(value, float) and value != value:  # NaN
                continue
            else:
                sheet.write(row_idx, col, value)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


async def db_totals(dataset_id: str) -> tuple[int, float]:
    """(row count, revenue sum) straight from PostgreSQL."""
    import uuid

    from app.db.models import SalesRecord
    from app.db.session import get_sessionmaker
    from sqlalchemy import func, select

    async with get_sessionmaker()() as session:
        row = (
            await session.execute(
                select(func.count(), func.coalesce(func.sum(SalesRecord.revenue), 0)).where(
                    SalesRecord.dataset_id == uuid.UUID(dataset_id)
                )
            )
        ).one()
    return int(row[0]), float(row[1])
