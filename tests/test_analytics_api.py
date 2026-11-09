import asyncio
import io
from datetime import date, timedelta

import pandas as pd
import pytest
from app.services.analytics import frames
from app.services.analytics.frames import get_frame_cache

from tests.helpers import FULL_MAPPING, sales_csv, upload, upload_and_wait

SOURCE_ARGS = dict(days=150, seed=21)


@pytest.fixture
async def dataset(client):
    csv = sales_csv(**SOURCE_ARGS)
    ds = await upload_and_wait(client, csv, "sales.csv", mapping=FULL_MAPPING)
    assert ds["status"] == "ready"
    return ds, pd.read_csv(io.BytesIO(csv))


def url(ds, path, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"/api/datasets/{ds['id']}/analytics/{path}" + (f"?{query}" if query else "")


def assert_camel_case(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            assert "_" not in key, f"snake_case key leaked into the API: {key}"
            assert_camel_case(inner)
    elif isinstance(value, list):
        for item in value:
            assert_camel_case(item)


async def test_overview_contract_and_values(client, dataset):
    ds, source = dataset
    response = await client.get(url(ds, "overview"))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"period", "kpis", "revenueTrend", "topProducts", "categories", "regions", "insights"}
    assert_camel_case(body)
    assert body["period"] == ds["dateRange"]

    kpis = {k["id"]: k for k in body["kpis"]}
    assert list(kpis)[:4] == ["revenue", "orders", "units", "aov"] and {"profit", "margin"} <= set(kpis)
    assert kpis["revenue"]["value"] == pytest.approx(source["Revenue"].sum(), abs=0.01)
    assert kpis["orders"]["value"] == source["Order ID"].nunique()  # distinct orders, not rows
    assert kpis["units"]["value"] == source["Quantity"].sum()
    assert kpis["margin"]["hint"] == "Change in percentage points" and kpis["margin"]["format"] == "percent"
    assert all(k["change"] is None for k in body["kpis"])  # no comparison requested
    assert "inverse" not in kpis["revenue"]  # optional TS fields are omitted, not null

    trend = body["revenueTrend"]
    assert [p["date"][-2:] for p in trend] == ["01"] * len(trend) and [p["date"] for p in trend] == sorted(
        p["date"] for p in trend
    )
    assert sum(p["revenue"] for p in trend) == pytest.approx(source["Revenue"].sum(), abs=0.05)
    assert {"cost", "profit", "margin"} <= set(trend[0])
    assert len(body["topProducts"]) == 5 and body["topProducts"] == sorted(
        body["topProducts"], key=lambda p: -p["revenue"]
    )
    assert 1 <= len(body["insights"]) <= 4
    assert set(body["insights"][0]) >= {"id", "type", "title", "summary", "evidence"}


async def test_category_region_and_date_filters_reach_the_engine(client, dataset):
    ds, source = dataset
    apparel = source[source["Category"] == "Apparel"]["Revenue"].sum()
    two = source[source["Category"].isin(["Apparel", "Electronics"])]["Revenue"].sum()
    north_home = source[(source["Region"] == "North") & (source["Category"] == "Home & Living")]["Revenue"].sum()

    async def revenue(**params):
        body = (await client.get(url(ds, "overview", **params))).json()
        return body["kpis"][0]["value"], body

    assert (await revenue(categories="Apparel"))[0] == pytest.approx(apparel, abs=0.01)
    assert (await revenue(categories="Apparel&categories=Electronics"))[0] == pytest.approx(
        two, abs=0.01
    )  # repeated param
    assert (await revenue(categories="Home %26 Living&regions=North"))[0] == pytest.approx(
        north_home, abs=0.01
    )  # URL-encoded &
    value, empty = await revenue(categories="Nonexistent")
    assert value == 0 and empty["revenueTrend"] == [] and empty["insights"] == [] and empty["topProducts"] == []

    last = date.fromisoformat(ds["dateRange"]["to"])
    _, body = await revenue(datePreset="last_30d")
    assert body["period"] == {
        "from": str(last - timedelta(days=29)),
        "to": str(last),
    }  # relative to the data, not today
    _, body = await revenue(datePreset="ytd")
    assert body["period"]["from"] == f"{last.year}-01-01"
    _, body = await revenue(datePreset="custom", dateFrom="2026-02-01", dateTo="2026-02-28")
    assert body["period"] == {"from": "2026-02-01", "to": "2026-02-28"}
    feb = source[(source["Order Date"] >= "2026-02-01") & (source["Order Date"] <= "2026-02-28")]["Revenue"].sum()
    assert body["kpis"][0]["value"] == pytest.approx(feb, abs=0.01)


async def test_previous_period_comparison(client, dataset):
    ds, _ = dataset
    body = (
        await client.get(url(ds, "sales", datePreset="last_90d", comparison="previous_period", groupBy="week"))
    ).json()
    assert body["previousTrend"] and all(isinstance(k["change"], float) for k in body["kpis"])
    assert len(body["previousTrend"]) in (len(body["trend"]) - 1, len(body["trend"]), len(body["trend"]) + 1)

    plain = (await client.get(url(ds, "sales", datePreset="last_90d", comparison="none"))).json()
    assert plain["previousTrend"] is None and all(k["change"] is None for k in plain["kpis"])

    # "all time" has nothing before it: the comparison is ignored, never an error
    all_time = (await client.get(url(ds, "sales", comparison="previous_period"))).json()
    assert all_time["previousTrend"] is None


async def test_daily_series_is_zero_filled_across_days_without_sales(client, dataset):
    ds, source = dataset
    body = (await client.get(url(ds, "sales", groupBy="day"))).json()
    days = (date.fromisoformat(ds["dateRange"]["to"]) - date.fromisoformat(ds["dateRange"]["from"])).days + 1
    assert len(body["trend"]) == days > source["Order Date"].nunique()  # gap days are present...
    gaps = [p for p in body["trend"] if p["revenue"] == 0]
    assert gaps and all(p["orders"] == 0 and p["aov"] == 0 and "margin" not in p for p in gaps)  # ...as honest zeros
    dates = [date.fromisoformat(p["date"]) for p in body["trend"]]
    assert all(b - a == timedelta(days=1) for a, b in zip(dates, dates[1:], strict=False))


async def test_weekly_buckets_start_on_monday(client, dataset):
    ds, _ = dataset
    body = (await client.get(url(ds, "sales", groupBy="week"))).json()
    assert {date.fromisoformat(p["date"]).weekday() for p in body["trend"]} == {0}


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"groupBy": "year"}, "validation_error"),
        ({"datePreset": "forever"}, "validation_error"),
        ({"comparison": "yoy"}, "validation_error"),
        ({"dateFrom": "garbage"}, "validation_error"),
        ({"datePreset": "custom", "dateFrom": "2026-03-01", "dateTo": "2026-02-01"}, "invalid_date_range"),
        ({"currency": "XXXX"}, "validation_error"),
        ({"currency": "ZZZ"}, "invalid_format_settings"),
        ({"locale": "zz-ZZ"}, "invalid_format_settings"),
    ],
)
async def test_invalid_query_parameters_are_422(client, dataset, params, code):
    ds, _ = dataset
    for endpoint in ("overview", "sales", "insights"):
        response = await client.get(url(ds, endpoint, **params))
        assert response.status_code == 422, (endpoint, response.text)
        assert response.json()["code"] == code and response.json()["message"]


async def test_customers_and_finance_payloads(client, dataset):
    ds, source = dataset
    customers = (await client.get(url(ds, "customers", datePreset="last_90d", comparison="previous_period"))).json()
    assert customers["available"] is True and set(customers) == {"available", "data"}
    data = customers["data"]
    assert set(data) == {"kpis", "newVsReturning", "distribution", "frequency", "segments"}
    assert_camel_case(customers)
    assert [k["id"] for k in data["kpis"]] == ["customers", "new", "returning", "rpc"]
    assert [b["label"] for b in data["frequency"]] == [
        "1 order",
        "2 orders",
        "3 orders",
        "4 orders",
        "5 orders",
        "6+ orders",
    ]
    assert [(s["name"], s["description"]) for s in data["segments"]] == [
        ("Champions", "6 or more orders"),
        ("Loyal", "3–5 orders"),
        ("Returning", "2 orders"),
        ("One-time", "1 order"),
    ]
    total = data["kpis"][0]["value"]
    assert sum(b["count"] for b in data["frequency"]) == total == sum(s["customers"] for s in data["segments"])
    assert data["kpis"][1]["value"] + data["kpis"][2]["value"] == total

    finance = (await client.get(url(ds, "finance"))).json()
    assert finance["available"] is True
    values = [m["value"] for m in finance["data"]["categoryMargins"]]
    assert values == sorted(values, reverse=True) and len(values) == source["Category"].nunique()
    kpis = {k["id"]: k for k in finance["data"]["kpis"]}
    assert kpis["cost"]["inverse"] is True and kpis["cost"]["value"] == pytest.approx(source["Cost"].sum(), abs=0.01)
    assert kpis["profit"]["value"] == pytest.approx(source["Revenue"].sum() - source["Cost"].sum(), abs=0.02)


async def test_capabilities_are_reported_unavailable_with_the_documented_reasons(client):
    ds = await upload_and_wait(client, sales_csv(days=60, customers=False, cost=False, regions=False))
    assert ds["capabilities"] == {"customers": False, "cost": False, "regions": False}

    customers = (await client.get(url(ds, "customers"))).json()
    assert customers == {
        "available": False,
        "reason": "This dataset has no customer column. Map a customer ID column when uploading to unlock customer analytics.",
    }
    finance = (await client.get(url(ds, "finance"))).json()
    assert finance["available"] is False and finance["reason"].startswith("This dataset has no cost column")

    overview = (await client.get(url(ds, "overview"))).json()
    assert {k["id"] for k in overview["kpis"]} == {"revenue", "orders", "units", "aov"}
    assert all("cost" not in p and "profit" not in p and "margin" not in p for p in overview["revenueTrend"])
    assert overview["regions"] == [] and overview["categories"]
    assert all(p["margin"] is None for p in overview["topProducts"])
    assert "low-margin" not in {i["id"] for i in overview["insights"]}


async def test_products_payload(client, dataset):
    ds, source = dataset
    body = (await client.get(url(ds, "products", datePreset="last_90d", comparison="previous_period"))).json()
    assert set(body) == {"top", "low", "all", "categories"}
    assert len(body["all"]) == source["Product"].nunique()
    assert [p["name"] for p in body["top"]] == [p["name"] for p in body["all"][:5]]
    assert [p["name"] for p in body["low"]] == [p["name"] for p in reversed(body["all"])][:5]  # weakest first
    assert len({p["id"] for p in body["all"]}) == len(body["all"])
    again = (await client.get(url(ds, "products", datePreset="last_90d", comparison="previous_period"))).json()
    assert [p["id"] for p in again["all"]] == [p["id"] for p in body["all"]]  # ids are stable
    assert sum(p["share"] for p in body["all"]) == pytest.approx(100, abs=0.01)


async def test_insights_are_phrased_by_the_server_in_the_requested_currency(client, dataset):
    ds, _ = dataset
    params = dict(datePreset="last_90d", comparison="previous_period")
    inr = (await client.get(url(ds, "insights", **params))).json()
    assert len(inr) > 4 and {i["type"] for i in inr} <= {
        "positive",
        "negative",
        "anomaly",
        "observation",
        "recommendation",
    }
    text = " ".join(i["title"] + i["summary"] + " ".join(e["value"] for e in i["evidence"]) for i in inr)
    assert "₹" in text and "$" not in text
    assert inr[0]["id"] == "revenue-change" and "vs the previous period" in inr[0]["title"]

    usd = (await client.get(url(ds, "insights", currency="USD", locale="en-US", **params))).json()
    text = " ".join(i["summary"] + " ".join(e["value"] for e in i["evidence"]) for i in usd)
    assert "$" in text and "₹" not in text


async def test_records_for_the_data_explorer(client, dataset):
    ds, source = dataset
    body = (await client.get(f"/api/datasets/{ds['id']}/records")).json()
    assert [c["key"] for c in body["columns"]] == [
        "orderId",
        "date",
        "product",
        "category",
        "region",
        "customerId",
        "quantity",
        "unitPrice",
        "revenue",
        "cost",
    ]
    assert body["total"] == len(source) == len(body["rows"]) and body["truncated"] is False
    assert [r["date"] for r in body["rows"]] == sorted((r["date"] for r in body["rows"]), reverse=True)  # newest first
    row = body["rows"][0]
    assert set(row) == {c["key"] for c in body["columns"]}
    assert row["unitPrice"] == pytest.approx(row["revenue"] / row["quantity"], abs=1e-3)
    assert isinstance(row["quantity"], int)

    page = (await client.get(f"/api/datasets/{ds['id']}/records?limit=10&offset=5")).json()
    assert (
        len(page["rows"]) == 10 and page["truncated"] is True and page["offset"] == 5 and page["total"] == len(source)
    )
    assert page["rows"] == body["rows"][5:15]  # stable ordering across pages
    assert (await client.get(f"/api/datasets/{ds['id']}/records?limit=0")).status_code == 422


async def test_explorer_only_lists_columns_the_user_provided(client):
    csv = b"Date,Product,Revenue\n2026-01-05,Tee,10\n2026-01-06,Lamp,5\n"
    ds = await upload_and_wait(client, csv, "min.csv")
    body = (await client.get(f"/api/datasets/{ds['id']}/records")).json()
    assert [c["key"] for c in body["columns"]] == ["date", "product", "revenue"]
    assert body["rows"] == [
        {"date": "2026-01-06", "product": "Lamp", "revenue": 5},
        {"date": "2026-01-05", "product": "Tee", "revenue": 10},
    ]


async def test_cached_and_database_loaded_frames_give_identical_answers(client, dataset):
    """The pipeline pre-warms the cache from the cleaned frame; a cold read goes through PostgreSQL.
    Both paths must produce exactly the same numbers."""
    ds, _ = dataset
    paths = [
        ("overview", {}),
        ("sales", {"groupBy": "week", "comparison": "previous_period", "datePreset": "last_90d"}),
        ("products", {}),
        ("customers", {}),
        ("finance", {}),
        ("insights", {}),
    ]
    assert len(get_frame_cache()) == 1  # warmed by the ingestion job
    warm = {p: (await client.get(url(ds, p, **q))).json() for p, q in paths}
    get_frame_cache().clear()
    cold = {p: (await client.get(url(ds, p, **q))).json() for p, q in paths}
    assert warm == cold
    assert len(get_frame_cache()) == 1


async def test_concurrent_cold_requests_share_a_single_database_load(client, dataset, monkeypatch):
    ds, _ = dataset
    get_frame_cache().clear()
    calls = 0
    original = frames.load_frame

    async def counting_load(session, dataset_id):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)  # widen the race window
        return await original(session, dataset_id)

    import app.api.routes.analytics as routes

    monkeypatch.setattr(routes, "load_frame", counting_load)
    responses = await asyncio.gather(*[client.get(url(ds, "overview")) for _ in range(8)])
    assert {r.status_code for r in responses} == {200} and len({r.text for r in responses}) == 1
    assert calls == 1  # single-flight: one read, seven waiters


async def test_unfinished_datasets_cannot_be_analysed_yet(client, monkeypatch):
    from app.services.ingestion import pipeline

    gate = asyncio.Event()

    async def blocked_copy(*args, **kwargs):
        await gate.wait()

    monkeypatch.setattr(pipeline, "copy_records", blocked_copy)
    response = await upload(client, sales_csv(days=20), mapping=FULL_MAPPING)
    dataset_id = response.json()["datasetId"]
    await asyncio.sleep(0.3)
    for path in ("analytics/overview", "analytics/customers", "records", "reports"):
        r = await client.get(f"/api/datasets/{dataset_id}/{path}")
        if path == "reports":  # the history of a dataset is readable at any time
            assert r.status_code == 200
        else:
            assert r.status_code == 409 and r.json()["code"] == "dataset_not_ready", path
    gate.set()
