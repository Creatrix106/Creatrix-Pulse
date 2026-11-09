import asyncio
import io
import uuid
from datetime import timedelta

import pandas as pd
from app.db.base import utcnow
from app.db.models import Dataset
from app.db.session import get_sessionmaker
from app.services import datasets as dataset_service
from app.services.jobs import jobs
from sqlalchemy import update

from tests.conftest import new_client, register
from tests.helpers import (
    FULL_MAPPING,
    db_totals,
    display_frame,
    sales_csv,
    to_xls,
    to_xlsx,
    upload,
    upload_and_wait,
)

STAGE_LABELS = [
    "Uploading dataset",
    "Validating columns",
    "Processing records",
    "Generating analytics",
    "Preparing dashboard",
]


async def test_upload_processes_in_background_and_exposes_metadata(client):
    data = sales_csv(days=90)
    source = pd.read_csv(io.BytesIO(data))

    response = await upload(client, data, "monthly_sales-2026.csv", mapping=FULL_MAPPING)
    assert response.status_code == 202 and set(response.json()) == {"datasetId"}
    dataset_id = response.json()["datasetId"]
    await jobs.wait_idle(timeout=60)

    ds = (await client.get(f"/api/datasets/{dataset_id}")).json()
    assert ds["status"] == "ready" and "errorMessage" not in ds
    assert ds["name"] == "monthly sales 2026" and ds["fileName"] == "monthly_sales-2026.csv"
    assert ds["fileSize"] == len(data)
    assert ds["rowCount"] == len(source) and ds["columnCount"] == 9
    assert ds["dateRange"] == {"from": source["Order Date"].min(), "to": source["Order Date"].max()}
    assert ds["capabilities"] == {"customers": True, "cost": True, "regions": True}
    assert ds["filterOptions"] == {
        "categories": sorted(source["Category"].unique()),
        "regions": sorted(source["Region"].unique()),
    }
    types = {c["name"]: (c["type"], c.get("mappedTo")) for c in ds["columns"]}
    assert types["Order Date"] == ("date", "date")
    assert types["Revenue"] == ("number", "revenue") and types["Customer ID"] == ("string", "customer")
    assert [c["name"] for c in ds["columns"]] == list(source.columns)  # file order

    count, revenue = await db_totals(dataset_id)
    assert count == len(source) and abs(revenue - source["Revenue"].sum()) < 0.01  # nothing lost, nothing invented

    status = (await client.get(f"/api/datasets/{dataset_id}/processing")).json()
    assert status["status"] == "ready" and status["progress"] == 100 and "message" not in status
    assert [(s["label"], s["status"]) for s in status["stages"]] == [(label, "complete") for label in STAGE_LABELS]
    assert [s["id"] for s in status["stages"]] == ["upload", "validate", "process", "analytics", "prepare"]


async def test_in_flight_processing_reports_real_stage_and_progress(client, monkeypatch):
    """Freeze the job inside the COPY stage and look at what a polling client sees."""
    from app.services.ingestion import pipeline

    reached, release = asyncio.Event(), asyncio.Event()

    async def slow_copy(conninfo, dataset_id, frame, *, chunk_rows, on_progress=None):
        await on_progress(len(frame) // 2, len(frame))  # half of the rows written
        reached.set()
        await release.wait()
        await on_progress(len(frame), len(frame))

    monkeypatch.setattr(pipeline, "copy_records", slow_copy)
    response = await upload(client, sales_csv(days=60), mapping=FULL_MAPPING)
    dataset_id = response.json()["datasetId"]
    await asyncio.wait_for(reached.wait(), 30)

    mid = (await client.get(f"/api/datasets/{dataset_id}/processing")).json()
    assert mid["status"] == "processing"
    assert [s["status"] for s in mid["stages"]] == ["complete", "complete", "active", "pending", "pending"]
    assert 15 < mid["progress"] < 85  # derived from rows written, not from a timer
    listed = (await client.get("/api/datasets")).json()[0]
    assert listed["status"] == "processing" and listed["rowCount"] > 0  # row count is known once parsed

    release.set()
    await jobs.wait_idle(timeout=30)
    assert (await client.get(f"/api/datasets/{dataset_id}")).json()["status"] == "ready"


async def test_list_returns_newest_first_and_get_unknown_is_404(client):
    first = await upload_and_wait(client, sales_csv(days=40), "first.csv", mapping=FULL_MAPPING)
    second = await upload_and_wait(client, sales_csv(days=40, seed=9), "second.csv", mapping=FULL_MAPPING)
    listed = (await client.get("/api/datasets")).json()
    assert [d["id"] for d in listed] == [second["id"], first["id"]]

    for bad_id in [str(uuid.uuid4()), "demo-retail", "not-a-uuid", "12345", "%27%3B--"]:
        response = await client.get(f"/api/datasets/{bad_id}")
        assert response.status_code == 404, bad_id
        assert response.json() == {
            "code": "dataset_not_found",
            "message": "This dataset does not exist or was deleted.",
        }

    # path-traversal style ids never reach the lookup: still a clean JSON 404 from the router
    response = await client.get("/api/datasets/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 404 and set(response.json()) == {"code", "message"}


async def test_upload_input_validation(client):
    csv = sales_csv(days=20)
    cases = [
        (await upload(client, b"%PDF-1.4", "report.pdf", content_type="application/pdf"), 415, "unsupported_file_type"),
        (await upload(client, b"", "empty.csv"), 422, "empty_file"),
        (
            await client.post(
                "/api/datasets", files={"file": ("a.csv", csv, "text/csv")}, data={"mapping": "{not json"}
            ),
            422,
            "invalid_mapping",
        ),
        (
            await client.post(
                "/api/datasets", files={"file": ("a.csv", csv, "text/csv")}, data={"mapping": '{"nonsense": "X"}'}
            ),
            422,
            "invalid_mapping",
        ),
        (await client.post("/api/datasets", data={"mapping": "{}"}), 422, "validation_error"),
    ]
    for response, status, code in cases:
        assert response.status_code == status and response.json()["code"] == code, response.text
    assert (await client.get("/api/datasets")).json() == []  # nothing was created by rejected uploads


async def test_upload_size_limits(client):
    # MAX_UPLOAD_MB=2 in the test environment. Pad a valid CSV with a long comment-free trailing text column.
    row = b"2026-01-01,Tee,10," + b"x" * 1000 + b"\n"
    just_over = b"Date,Product,Revenue,Notes\n" + row * 2100  # ~2.1 MB: rejected by the exact check
    response = await upload(client, just_over, "big.csv")
    assert response.status_code == 413 and response.json()["code"] == "file_too_large"
    assert "maximum size is 2 MB" in response.json()["message"]

    way_over = b"Date,Product,Revenue,Notes\n" + row * 4000  # ~4 MB: rejected from Content-Length alone
    response = await upload(client, way_over, "huge.csv")
    assert response.status_code == 413 and response.json()["code"] == "payload_too_large"


async def test_bad_data_fails_with_a_clear_message_and_leaves_nothing_behind(client):
    bad = b"Date,Product,Revenue\n2026-01-05,Tee,10\nnot-a-date,Lamp,5\n,Bag,3\n"
    ds = await upload_and_wait(
        client, bad, "bad.csv", mapping={"date": "Date", "product": "Product", "revenue": "Revenue"}
    )
    assert ds["status"] == "failed" and ds["rowCount"] == 0 and ds["dateRange"] is None
    assert "date column “Date” could not be read in 2 rows" in ds["errorMessage"]
    assert "row 3: “not-a-date”" in ds["errorMessage"]

    status = (await client.get(f"/api/datasets/{ds['id']}/processing")).json()
    assert status["status"] == "failed" and status["progress"] is None and status["message"] == ds["errorMessage"]
    assert [s["status"] for s in status["stages"]] == ["complete", "failed", "pending", "pending", "pending"]
    assert (await db_totals(ds["id"]))[0] == 0

    # analytics on a failed dataset is a clean 409, not a crash
    response = await client.get(f"/api/datasets/{ds['id']}/analytics/overview")
    assert response.status_code == 409 and response.json()["code"] == "dataset_not_ready"


async def test_excel_workbooks_are_detected_without_a_mapping(client):
    frame = display_frame(days=60, seed=5)
    expected_revenue = float(frame["Revenue"].sum())
    for name, data in (("book.xlsx", to_xlsx(frame)), ("legacy.xls", to_xls(frame))):
        ds = await upload_and_wait(client, data, name)  # empty mapping, like the browser sends for Excel
        assert ds["status"] == "ready", ds
        assert ds["rowCount"] == len(frame)
        assert ds["capabilities"] == {"customers": True, "cost": True, "regions": True}
        mapped = {c["mappedTo"] for c in ds["columns"] if "mappedTo" in c}
        assert mapped == {"date", "orderId", "product", "category", "region", "customer", "quantity", "revenue", "cost"}
        count, revenue = await db_totals(ds["id"])
        assert count == len(frame) and abs(revenue - expected_revenue) < 0.01, name


async def test_excel_without_required_columns_fails_helpfully(client):
    frame = pd.DataFrame({"Foo": [1, 2], "Bar": ["a", "b"]})
    ds = await upload_and_wait(client, to_xlsx(frame), "nope.xlsx")
    assert ds["status"] == "failed" and "couldn't find a column for" in ds["errorMessage"]


async def test_semicolon_cp1252_csv_from_european_excel(client):
    text = "Order Date;Product;Revenue\n2026-01-05;Café Mug;1,299.50\n2026-01-06;Tee;800\n"
    ds = await upload_and_wait(client, text.encode("cp1252"), "euro.csv")  # no mapping: auto-detected
    assert ds["status"] == "ready" and ds["rowCount"] == 2
    assert abs((await db_totals(ds["id"]))[1] - 2099.5) < 0.001


async def test_replace_removes_the_old_dataset_only_after_success(client):
    old = await upload_and_wait(client, sales_csv(days=40), "old.csv", mapping=FULL_MAPPING)

    # a failing replacement keeps the old dataset
    failed = await upload_and_wait(client, b"Date,Product,Revenue\nx,y,z\n", "broken.csv", replace=old["id"])
    assert failed["status"] == "failed"
    assert (await client.get(f"/api/datasets/{old['id']}")).status_code == 200

    # a successful replacement removes it (rows included)
    new = await upload_and_wait(client, sales_csv(days=40, seed=4), "new.csv", mapping=FULL_MAPPING, replace=old["id"])
    assert new["status"] == "ready"
    assert (await client.get(f"/api/datasets/{old['id']}")).status_code == 404
    assert (await db_totals(old["id"]))[0] == 0
    assert {d["id"] for d in (await client.get("/api/datasets")).json()} == {new["id"], failed["id"]}


async def test_users_cannot_see_touch_or_replace_each_others_datasets(client, other_client):
    mine = await upload_and_wait(client, sales_csv(days=30), "mine.csv", mapping=FULL_MAPPING)
    assert (await other_client.get("/api/datasets")).json() == []
    for method, path in [
        ("GET", ""),
        ("GET", "/processing"),
        ("DELETE", ""),
        ("GET", "/analytics/overview"),
        ("GET", "/records"),
    ]:
        response = await other_client.request(method, f"/api/datasets/{mine['id']}{path}")
        assert response.status_code == 404 and response.json()["code"] == "dataset_not_found", path

    # smuggling someone else's dataset id into "replace" must not delete it
    theirs = await upload_and_wait(
        other_client, sales_csv(days=30, seed=2), "t.csv", mapping=FULL_MAPPING, replace=mine["id"]
    )
    assert theirs["status"] == "ready"
    assert (await client.get(f"/api/datasets/{mine['id']}")).status_code == 200


async def test_delete_removes_dataset_records_and_reports(client):
    ds = await upload_and_wait(client, sales_csv(days=30), "d.csv", mapping=FULL_MAPPING)
    report = await client.post(
        f"/api/datasets/{ds['id']}/reports",
        json={"title": "T", "metrics": ["revenue"], "datePreset": "all", "format": "csv"},
    )
    assert report.status_code == 201
    assert (await client.delete(f"/api/datasets/{ds['id']}")).status_code == 204
    assert (await client.get(f"/api/datasets/{ds['id']}")).status_code == 404
    assert (await client.delete(f"/api/datasets/{ds['id']}")).status_code == 404
    assert (await db_totals(ds["id"]))[0] == 0


async def test_viewers_can_read_but_not_change_data(app):
    async with new_client(app) as viewer:
        await register(viewer, role="viewer")
        assert (await viewer.get("/api/datasets")).status_code == 200
        denied = await upload(viewer, sales_csv(days=10), "v.csv")
        assert denied.status_code == 403 and denied.json()["code"] == "insufficient_role"
        assert (await viewer.delete(f"/api/datasets/{uuid.uuid4()}")).status_code == 403


async def test_abandoned_processing_jobs_are_failed_instead_of_hanging_forever(client):
    ds = await upload_and_wait(client, sales_csv(days=20), "x.csv", mapping=FULL_MAPPING)
    async with get_sessionmaker()() as session:  # simulate a worker that died mid-COPY 10 minutes ago
        await session.execute(
            update(Dataset)
            .where(Dataset.id == uuid.UUID(ds["id"]))
            .values(status="processing", stage="process", progress=40, updated_at=utcnow() - timedelta(minutes=10))
        )
        await session.commit()
    status = (await client.get(f"/api/datasets/{ds['id']}/processing")).json()
    assert status["status"] == "failed" and status["message"] == dataset_service.INTERRUPTED_MESSAGE
    assert [s["status"] for s in status["stages"]] == ["complete", "complete", "failed", "pending", "pending"]
    assert (await db_totals(ds["id"]))[0] == 0  # partial rows were removed


async def test_users_cannot_flood_the_server_with_parallel_uploads(client):
    me = (await client.get("/api/auth/me")).json()["id"]
    async with get_sessionmaker()() as session:
        for i in range(3):
            session.add(
                Dataset(
                    owner_id=uuid.UUID(me),
                    name=f"p{i}",
                    file_name=f"p{i}.csv",
                    file_size=1,
                    status="processing",
                    stage="process",
                )
            )
        await session.commit()
    response = await upload(client, sales_csv(days=10), "more.csv")
    assert response.status_code == 429 and response.json()["code"] == "too_many_uploads"


async def test_the_main_browser_flow_custom_headers_mapped_by_the_user_with_extra_columns(client):
    csv = (
        b"Sold On,Item,Gross,Payment,Ref\n"
        b"2026-01-05,Tee,100,UPI,1\n"
        b"2026-01-06,Lamp,250.50,Card,2\n"
        b"2026-02-01,Tee,100,UPI,3\n"
    )
    mapping = {"date": "Sold On", "product": "Item", "revenue": "Gross"}  # exactly what the mapping step sends
    ds = await upload_and_wait(client, csv, "my_export.csv", mapping=mapping)
    assert ds["status"] == "ready" and ds["name"] == "my export"
    assert ds["rowCount"] == 3 and ds["columnCount"] == 5  # every column of the file is reported...
    assert {c["name"]: c.get("mappedTo") for c in ds["columns"]} == {
        "Sold On": "date",
        "Item": "product",
        "Gross": "revenue",
        "Payment": None,
        "Ref": None,
    }  # ...but only the mapped ones carry `mappedTo`
    assert ds["capabilities"] == {"customers": False, "cost": False, "regions": False}
    assert ds["filterOptions"] == {"categories": [], "regions": []}

    overview = (await client.get(f"/api/datasets/{ds['id']}/analytics/overview")).json()
    assert overview["kpis"][0]["value"] == 450.5
    assert (
        overview["kpis"][1]["value"] == 3 and overview["kpis"][2]["value"] == 3
    )  # no order id / quantity: 1 row = 1 order = 1 unit
    assert [(p["name"], p["revenue"]) for p in overview["topProducts"]] == [("Lamp", 250.5), ("Tee", 200)]  # by revenue
    assert overview["categories"] == [] and overview["regions"] == []  # never invented
    assert overview["topProducts"][0]["category"] == "Uncategorized"

    records = (await client.get(f"/api/datasets/{ds['id']}/records")).json()
    assert [c["key"] for c in records["columns"]] == ["date", "product", "revenue"]


async def test_upload_without_a_mapping_field_detects_columns(client):
    response = await client.post(
        "/api/datasets", files={"file": ("a.csv", b"Date,Product,Revenue\n2026-01-05,Tee,10\n", "text/csv")}
    )
    assert response.status_code == 202
    await jobs.wait_idle(timeout=30)
    assert (await client.get(f"/api/datasets/{response.json()['datasetId']}")).json()["status"] == "ready"
