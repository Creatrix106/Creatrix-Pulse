"""Contract test: real backend responses must type-check against the frontend's own TypeScript API types.

It drives the app through every endpoint, every Capability branch, failed / in-flight / ready datasets and the
error bodies, writes the JSON it got back as *typed literals* into a .ts file, and runs `tsc --strict`. A renamed
key, a wrong type, a missing field or a stray `null` becomes a compile error. A second test proves the check has
teeth: it damages the responses one way at a time and requires tsc to object to every mutation.

Needs the frontend's `src/types` directory (env FRONTEND_TYPES_DIR; default: ../Creatrix-Pulse--frontend/my-app/src/types
next to this repository) and `npm install` inside tests/contract (TypeScript 5.9.3, the version the frontend pins).
Skipped when either is missing.
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path

import pytest
from app.services.jobs import jobs

from tests.helpers import FULL_MAPPING, sales_csv, upload, upload_and_wait

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONTRACT = HERE / "contract"
BUILD = CONTRACT / ".build"
TSC = CONTRACT / "node_modules" / ".bin" / "tsc"
TYPES = Path(
    os.environ.get("FRONTEND_TYPES_DIR", ROOT.parent / "Creatrix-Pulse--frontend" / "my-app" / "src" / "types")
)

pytestmark = pytest.mark.skipif(
    not (TSC.exists() and (TYPES / "analytics.ts").exists()),
    reason="needs the frontend's src/types (FRONTEND_TYPES_DIR) and `npm install` in tests/contract",
)

#: TypeScript type -> module of the frontend's src/types it is imported from
IMPORTS = {
    "User": "auth",
    "ApiErrorBody": "api",
    "Dataset": "dataset",
    "ProcessingStatus": "dataset",
    "UploadResult": "dataset",
    "OverviewData": "analytics",
    "SalesData": "analytics",
    "ProductsData": "analytics",
    "CustomersResponse": "analytics",
    "FinanceResponse": "analytics",
    "ExplorerData": "analytics",
    "Insight": "insight",
    "ReportPreview": "report",
    "ReportRecord": "report",
}
EXPLORER = (
    "ExplorerData & { total: number; truncated: boolean; limit: number; offset: number }"  # + additive paging fields
)
ANALYTICS = [
    ("overview", "OverviewData"),
    ("sales", "SalesData"),
    ("products", "ProductsData"),
    ("customers", "CustomersResponse"),
    ("finance", "FinanceResponse"),
    ("insights", "Insight[]"),
]
QUERIES = {
    "default filters": "",
    "90d vs previous, weekly": "?datePreset=last_90d&comparison=previous_period&groupBy=week",
    "custom range, daily, filtered": "?datePreset=custom&dateFrom=2026-02-01&dateTo=2026-02-20&groupBy=day&categories=Apparel&regions=North&regions=South",
    "selection with no rows": "?categories=Nonexistent",
}
REPORT = {
    "title": "Monthly performance",
    "metrics": ["revenue", "orders", "units", "aov", "cost", "profit"],
    "datePreset": "last_90d",
    "format": "csv",
}


class Recorder:
    """Collects (label, TypeScript type, JSON value) triples."""

    def __init__(self, items: list[tuple[str, str, object]] | None = None) -> None:
        self.items = items or []

    def add(self, label: str, ts_type: str, value: object) -> None:
        self.items.append((label, ts_type, value))

    def find(self, prefix: str) -> object:
        return next(value for label, _, value in self.items if label.startswith(prefix))

    def copy(self) -> Recorder:
        return Recorder([(label, ts, json.loads(json.dumps(value))) for label, ts, value in self.items])

    def source(self) -> str:
        rel = os.path.relpath(TYPES, BUILD).replace(os.sep, "/")
        lines = [f'import type {{ {name} }} from "{rel}/{module}";' for name, module in IMPORTS.items()] + [""]
        for index, (label, ts_type, value) in enumerate(self.items):
            lines += [f"// {label}", f"export const c{index}: {ts_type} = {json.dumps(value, ensure_ascii=False)};"]
        return "\n".join(lines) + "\n"


def run_tsc(source: str) -> subprocess.CompletedProcess[str]:
    BUILD.mkdir(exist_ok=True)
    for stale in BUILD.glob("*.ts"):
        stale.unlink()
    (BUILD / "contract.ts").write_text(source)
    return subprocess.run(  # noqa: S603
        [str(TSC), "-p", str(CONTRACT / "tsconfig.json")], capture_output=True, text=True, cwd=CONTRACT, timeout=180
    )


async def collect(client, other_client, anon, monkeypatch) -> Recorder:
    rec = Recorder()

    async def get(label, ts_type, url):
        response = await client.get(url)
        assert response.status_code == 200, (label, response.text)
        rec.add(label, ts_type, response.json())

    # ---- auth -----------------------------------------------------------------------------------
    rec.add("register", "User", client.user)
    await get("me", "User", "/api/auth/me")
    login = await client.post("/api/auth/login", json={"email": client.user["email"], "password": "Passw0rdOK"})
    rec.add("login", "User", login.json())
    rec.add(
        "401 invalid credentials",
        "ApiErrorBody",
        (await client.post("/api/auth/login", json={"email": client.user["email"], "password": "wrong-pass"})).json(),
    )
    rec.add(
        "422 validation error (with details)",
        "ApiErrorBody",
        (
            await client.post("/api/auth/register", json={"name": "A", "email": "x@example.com", "password": "abc"})
        ).json(),
    )

    # ---- a dataset with every capability --------------------------------------------------------
    full = await upload_and_wait(client, sales_csv(days=200, seed=31), "full.csv", mapping=FULL_MAPPING)
    rec.add("dataset (ready, all capabilities)", "Dataset", full)
    await get("processing (ready)", "ProcessingStatus", f"/api/datasets/{full['id']}/processing")
    for name, ts_type in ANALYTICS:
        for label, query in QUERIES.items():
            await get(f"{name} / {label}", ts_type, f"/api/datasets/{full['id']}/analytics/{name}{query}")
    await get("records", EXPLORER, f"/api/datasets/{full['id']}/records?limit=25")

    # ---- a dataset without customers / cost / regions (the `available: false` branches) -------------
    lean = await upload_and_wait(
        client, sales_csv(days=90, seed=2, customers=False, cost=False, regions=False), "lean.csv"
    )
    rec.add("dataset (ready, no capabilities)", "Dataset", lean)
    for name, ts_type in ANALYTICS:
        await get(
            f"lean {name}",
            ts_type,
            f"/api/datasets/{lean['id']}/analytics/{name}?comparison=previous_period&datePreset=last_30d",
        )
    await get("lean records", EXPLORER, f"/api/datasets/{lean['id']}/records")
    await get("datasets list", "Dataset[]", "/api/datasets")

    # ---- a failed dataset --------------------------------------------------------------------------
    failed = await upload_and_wait(client, b"Date,Product,Revenue\nx,y,z\n", "broken.csv")
    rec.add("dataset (failed, has errorMessage)", "Dataset", failed)
    await get("processing (failed, has message)", "ProcessingStatus", f"/api/datasets/{failed['id']}/processing")
    rec.add(
        "409 dataset_not_ready",
        "ApiErrorBody",
        (await client.get(f"/api/datasets/{failed['id']}/analytics/overview")).json(),
    )

    # ---- a dataset caught mid-flight -----------------------------------------------------------------
    from app.services.ingestion import pipeline

    reached, release = asyncio.Event(), asyncio.Event()

    async def slow_copy(conninfo, dataset_id, frame, *, chunk_rows, on_progress=None):
        await on_progress(len(frame) // 2, len(frame))
        reached.set()
        await release.wait()

    monkeypatch.setattr(pipeline, "copy_records", slow_copy)
    response = await upload(client, sales_csv(days=40, seed=5), "slow.csv", mapping=FULL_MAPPING)
    rec.add("202 upload result", "UploadResult", response.json())
    slow_id = response.json()["datasetId"]
    await asyncio.wait_for(reached.wait(), 30)
    await get("processing (in flight, numeric progress)", "ProcessingStatus", f"/api/datasets/{slow_id}/processing")
    await get("dataset (in flight)", "Dataset", f"/api/datasets/{slow_id}")
    release.set()
    await jobs.wait_idle(timeout=30)

    # ---- reports ----------------------------------------------------------------------------------------
    rec.add(
        "report preview",
        "ReportPreview",
        (await client.post(f"/api/datasets/{full['id']}/reports/preview", json=REPORT)).json(),
    )
    for fmt in ("csv", "json"):
        created = await client.post(f"/api/datasets/{full['id']}/reports", json={**REPORT, "format": fmt})
        assert created.status_code == 201
        rec.add(f"report record ({fmt})", "ReportRecord", created.json())
    await get("report history", "ReportRecord[]", f"/api/datasets/{full['id']}/reports")
    rec.add(
        "report preview (no cost)",
        "ReportPreview",
        (await client.post(f"/api/datasets/{lean['id']}/reports/preview", json=REPORT)).json(),
    )

    # ---- remaining error bodies --------------------------------------------------------------------------
    bad_range = f"/api/datasets/{full['id']}/analytics/overview?datePreset=custom&dateFrom=2026-03-01&dateTo=2026-02-01"
    for label, response in [
        ("404 dataset_not_found", await client.get("/api/datasets/unknown")),
        ("404 report_not_found", await client.get(f"/api/datasets/{full['id']}/reports/{full['id']}/download")),
        ("422 invalid_date_range", await client.get(bad_range)),
        ("404 someone else's dataset", await other_client.get(f"/api/datasets/{full['id']}")),
        ("401 not_authenticated", await anon.get("/api/datasets")),
    ]:
        rec.add(label, "ApiErrorBody", response.json())
    return rec


async def test_backend_responses_satisfy_the_frontend_types(client, other_client, anon, monkeypatch):
    recorder = await collect(client, other_client, anon, monkeypatch)
    assert len(recorder.items) >= 50  # every endpoint x every capability branch x several filter sets
    result = run_tsc(recorder.source())
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"[:6000]


#: name -> (label of the recorded response to damage, how to damage it)
MUTATIONS = {
    "wrong value type": ("overview / default filters", lambda v: v["kpis"][0].__setitem__("value", "12")),
    "renamed key": ("dataset (ready, all capabilities)", lambda v: v.__setitem__("filename", v.pop("fileName"))),
    "snake_case leak": ("dataset (ready, all capabilities)", lambda v: v.__setitem__("row_count", v.pop("rowCount"))),
    "null where only undefined is allowed": (
        "sales / default filters",
        lambda v: v["trend"][0].__setitem__("cost", None),
    ),
    "value outside a union": ("dataset (ready, all capabilities)", lambda v: v.__setitem__("status", "done")),
    "missing required field": ("overview / default filters", lambda v: v.pop("insights")),
    "unexpected extra field": ("me", lambda v: v.__setitem__("passwordHash", "x")),
    "unavailable capability without a reason": ("lean customers", lambda v: v.pop("reason")),
}


@pytest.mark.parametrize("name", list(MUTATIONS))
async def test_the_contract_check_really_detects_drift(name, client, other_client, anon, monkeypatch):
    """Negative control. The undamaged responses must pass (so tsc itself works), the damaged ones must fail, and
    the error must point into the generated contract file, i.e. at the mutated response."""
    label, damage = MUTATIONS[name]
    recorder = await collect(client, other_client, anon, monkeypatch)
    baseline = run_tsc(recorder.source())
    assert baseline.returncode == 0, baseline.stdout[:2000]

    mutant = recorder.copy()
    damage(mutant.find(label))
    result = run_tsc(mutant.source())
    assert result.returncode != 0, f"tsc did not notice: {name}"
    assert "contract.ts" in result.stdout, result.stdout[:2000]
