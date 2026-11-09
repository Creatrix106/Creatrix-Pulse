import csv
import io
import json

import pandas as pd
import pytest
from app.schemas.report import ReportPreviewOut
from app.services.reports import _cell

from tests.conftest import new_client, register
from tests.helpers import FULL_MAPPING, sales_csv, upload_and_wait

ALL_METRICS = ["revenue", "orders", "units", "aov", "cost", "profit"]
LABELS = ["Revenue", "Orders", "Units sold", "Average order value", "Cost", "Gross profit"]
CONFIG = {"title": "Monthly performance", "metrics": ALL_METRICS, "datePreset": "all", "format": "csv"}


@pytest.fixture
async def dataset(client):
    csv_bytes = sales_csv(days=150, seed=8)
    ds = await upload_and_wait(client, csv_bytes, "sales.csv", mapping=FULL_MAPPING)
    return ds, pd.read_csv(io.BytesIO(csv_bytes))


def base(ds):
    return f"/api/datasets/{ds['id']}/reports"


async def test_preview_contract(client, dataset):
    ds, source = dataset
    response = await client.post(f"{base(ds)}/preview", json=CONFIG)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"title", "generatedAt", "period", "summary", "columns", "rows"}
    assert body["title"] == "Monthly performance" and body["period"] == ds["dateRange"]
    assert body["columns"][0] == {"key": "date", "label": "Month", "format": "date"}
    assert [c["key"] for c in body["columns"][1:]] == ALL_METRICS
    assert [s["label"] for s in body["summary"]] == LABELS
    assert [c["format"] for c in body["columns"][1:]] == [
        "currency",
        "number",
        "number",
        "currency",
        "currency",
        "currency",
    ]

    summary = {s["label"]: s["value"] for s in body["summary"]}
    assert summary["Revenue"] == pytest.approx(source["Revenue"].sum(), abs=0.01)
    assert summary["Orders"] == source["Order ID"].nunique()
    assert summary["Gross profit"] == pytest.approx(source["Revenue"].sum() - source["Cost"].sum(), abs=0.02)

    months = [r["date"] for r in body["rows"]]
    assert months == sorted(months) and all(m.endswith("-01") for m in months)
    assert sum(r["revenue"] for r in body["rows"]) == pytest.approx(source["Revenue"].sum(), abs=0.05)
    assert set(body["rows"][0]) == {"date", *ALL_METRICS}


async def test_metrics_come_out_in_canonical_order_whatever_the_request_order(client, dataset):
    ds, _ = dataset
    body = (
        await client.post(f"{base(ds)}/preview", json={**CONFIG, "metrics": ["profit", "orders", "revenue"]})
    ).json()
    assert [c["key"] for c in body["columns"][1:]] == ["revenue", "orders", "profit"]


async def test_date_preset_limits_the_report_period(client, dataset):
    ds, _ = dataset
    everything = (await client.post(f"{base(ds)}/preview", json=CONFIG)).json()
    recent = (await client.post(f"{base(ds)}/preview", json={**CONFIG, "datePreset": "last_30d"})).json()
    assert recent["period"]["to"] == everything["period"]["to"]
    assert recent["period"]["from"] > everything["period"]["from"]
    assert sum(r["revenue"] for r in recent["rows"]) < sum(r["revenue"] for r in everything["rows"])


@pytest.mark.parametrize(
    "override",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
        {"metrics": []},
        {"metrics": ["revenue", "margin"]},
        {"format": "pdf"},
        {"datePreset": "someday"},
    ],
)
async def test_invalid_report_configs_are_rejected(client, dataset, override):
    ds, _ = dataset
    response = await client.post(f"{base(ds)}/preview", json={**CONFIG, **override})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert (await client.post(base(ds), json={**CONFIG, **override})).status_code == 422


async def test_cost_metrics_are_unavailable_without_cost_data(client):
    ds = await upload_and_wait(client, sales_csv(days=60, cost=False))
    ok = (await client.post(f"{base(ds)}/preview", json=CONFIG)).json()  # cost/profit are silently skipped
    assert [c["key"] for c in ok["columns"][1:]] == ["revenue", "orders", "units", "aov"]
    only_cost = await client.post(f"{base(ds)}/preview", json={**CONFIG, "metrics": ["cost", "profit"]})
    assert only_cost.status_code == 422 and only_cost.json()["code"] == "no_valid_metrics"


async def test_create_list_and_download_a_csv_report(client, dataset):
    ds, _ = dataset
    created = await client.post(base(ds), json=CONFIG)
    assert created.status_code == 201
    record = created.json()
    assert set(record) == {
        "id",
        "datasetId",
        "title",
        "format",
        "createdAt",
        "rowCount",
        "sizeBytes",
        "content",
        "downloadUrl",
    }
    assert record["title"] == "Monthly performance (All time)" and record["datasetId"] == ds["id"]
    assert record["downloadUrl"] == f"/api/datasets/{ds['id']}/reports/{record['id']}/download"
    assert record["sizeBytes"] == len(record["content"].encode())

    content = record["content"]
    assert not content.endswith("\n")  # same as the frontend's toCsv
    rows = list(csv.reader(io.StringIO(content)))
    assert rows[0] == ["Month", *LABELS]
    assert len(rows) - 1 == record["rowCount"] and rows[1][0].endswith("-01")
    assert all(cell and cell != "None" for row in rows for cell in row)
    assert "." not in rows[1][2]  # integral numbers print like JavaScript: 12, not 12.0

    listed = (await client.get(base(ds))).json()
    assert [r["id"] for r in listed] == [record["id"]] and listed[0]["content"] == content

    download = await client.get(record["downloadUrl"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "text/csv; charset=utf-8"
    assert download.headers["content-disposition"].startswith('attachment; filename="Monthly-performance-All-time.csv"')
    assert download.text == content


async def test_json_reports_embed_the_preview(client, dataset):
    ds, _ = dataset
    record = (await client.post(base(ds), json={**CONFIG, "format": "json", "metrics": ["revenue"]})).json()
    parsed = json.loads(record["content"])
    ReportPreviewOut.model_validate(parsed)  # it is a valid ReportPreview document
    assert parsed["title"] == "Monthly performance" and [c["key"] for c in parsed["columns"]] == ["date", "revenue"]
    assert record["content"].startswith('{\n  "title"')  # 2-space indented, like JSON.stringify(x, null, 2)
    download = await client.get(record["downloadUrl"])
    assert download.headers["content-type"] == "application/json; charset=utf-8"
    assert download.headers["content-disposition"].endswith("filename*=UTF-8''Monthly-performance-All-time.json")


async def test_history_is_newest_first(client, dataset):
    ds, _ = dataset
    ids = [(await client.post(base(ds), json={**CONFIG, "title": f"Report {i}"})).json()["id"] for i in range(3)]
    assert [r["id"] for r in (await client.get(base(ds))).json()] == ids[::-1]


async def test_reports_are_private_to_their_owner(client, other_client, dataset):
    ds, _ = dataset
    record = (await client.post(base(ds), json=CONFIG)).json()
    for method, url in [
        ("GET", base(ds)),
        ("POST", f"{base(ds)}/preview"),
        ("POST", base(ds)),
        ("GET", record["downloadUrl"]),
    ]:
        response = await other_client.request(method, url, json=CONFIG if method == "POST" else None)
        assert response.status_code == 404, url
        assert response.json()["code"] == "dataset_not_found"
    missing = await client.get(f"{base(ds)}/00000000-0000-0000-0000-000000000000/download")
    assert missing.status_code == 404 and missing.json()["code"] == "report_not_found"
    assert (await client.get(f"{base(ds)}/not-a-uuid/download")).json()["code"] == "report_not_found"


async def test_viewers_can_preview_but_not_save_reports(app, client, dataset):
    ds, _ = dataset
    async with new_client(app) as viewer:
        await register(viewer, role="viewer")
        # (another user's dataset is invisible to them; ownership is checked before the role)
        assert (await viewer.post(base(ds), json=CONFIG)).status_code in (403, 404)


def test_csv_cells_are_escaped_like_the_frontend_does():
    assert _cell("plain") == "plain"
    assert _cell('say "hi"') == '"say ""hi"""'
    assert _cell("a,b") == '"a,b"'
    assert _cell("line\nbreak") == '"line\nbreak"'
    assert _cell(12.0) == "12" and _cell(12.5) == "12.5" and _cell(7) == "7" and _cell(None) == ""
