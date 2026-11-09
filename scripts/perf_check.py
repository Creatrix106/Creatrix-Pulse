

import argparse
import io
import time
import uuid

import httpx
import numpy as np
import pandas as pd


def make_csv(target_mb: float, seed: int = 1) -> tuple[bytes, int]:
    rng = np.random.default_rng(seed)
    products = [f"Product {i:03d}" for i in range(120)]
    categories = ["Electronics", "Apparel", "Home & Living", "Personal Care", "Sports", "Toys", "Grocery", "Books"]
    regions = ["North", "South", "East", "West", "Central"]
    rows = int(target_mb * 1024 * 1024 / 86)  # ~86 bytes per row
    day = rng.integers(0, 3 * 365, rows)
    product = rng.integers(0, len(products), rows)
    qty = rng.integers(1, 6, rows)
    unit = np.round(rng.uniform(50, 5000, rows), 2)
    frame = pd.DataFrame(
        {
            "Order ID": [f"ORD-{i // 2:07d}" for i in range(rows)],  # two lines per order
            "Order Date": (pd.Timestamp("2024-01-01") + pd.to_timedelta(day, unit="D")).strftime("%Y-%m-%d"),
            "Product": np.array(products)[product],
            "Category": np.array(categories)[product % len(categories)],
            "Region": np.array(regions)[rng.integers(0, len(regions), rows)],
            "Customer ID": [f"C-{c:05d}" for c in rng.integers(0, 20000, rows)],
            "Quantity": qty,
            "Revenue": np.round(unit * qty, 2),
            "Cost": np.round(unit * qty * rng.uniform(0.4, 0.8, rows), 2),
        }
    )
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode(), rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000/api")
    parser.add_argument("--mb", type=float, default=24)
    parser.add_argument("--email", help="sign in as this user instead of registering a new one (use with --reuse)")
    parser.add_argument(
        "--reuse", action="store_true", help="skip the upload and time the first ready dataset (cold-cache test)"
    )
    args = parser.parse_args()

    with httpx.Client(base_url=args.base, timeout=300) as client:
        if args.reuse:
            assert client.post("/auth/login", json={"email": args.email, "password": "Passw0rdOK"}).status_code == 200
            dataset_id = next(d["id"] for d in client.get("/datasets").json() if d["status"] == "ready")
            time_endpoints(client, dataset_id, "cold (first read after a server restart: frame loaded from PostgreSQL)")
            time_endpoints(client, dataset_id, "warm (same endpoints again)")
            return

        started = time.perf_counter()
        data, rows = make_csv(args.mb)
        print(f"generated {len(data) / 1e6:.1f} MB CSV with {rows:,} rows in {time.perf_counter() - started:.1f}s")
        email = args.email or f"perf-{uuid.uuid4().hex[:8]}@example.com"
        print(f"user: {email}")
        assert (
            client.post("/auth/register", json={"name": "Perf", "email": email, "password": "Passw0rdOK"}).status_code
            == 201
        )

        t = time.perf_counter()
        response = client.post("/datasets", files={"file": ("big.csv", data, "text/csv")}, data={"mapping": "{}"})
        print(f"upload request: HTTP {response.status_code} in {time.perf_counter() - t:.2f}s")
        response.raise_for_status()
        dataset_id = response.json()["datasetId"]

        t, last = time.perf_counter(), None
        while True:
            status = client.get(f"/datasets/{dataset_id}/processing").json()
            marker = (status["status"], status["progress"])
            if marker != last:
                print(f"  +{time.perf_counter() - t:5.1f}s  {status['status']:11} progress={status['progress']}")
                last = marker
            if status["status"] in ("ready", "failed"):
                break
            time.sleep(0.25)
        print(
            f"processing finished in {time.perf_counter() - t:.1f}s -> {status['status']} {status.get('message', '')}"
        )
        dataset = client.get(f"/datasets/{dataset_id}").json()
        print(f"dataset: {dataset['rowCount']:,} rows, {dataset['dateRange']}")

        time_endpoints(client, dataset_id, "warm (frame cached by the ingestion job)")


def time_endpoints(client: httpx.Client, dataset_id: str, label: str) -> None:
    params = "?datePreset=last_180d&comparison=previous_period&groupBy=week"
    print(f"\n{label}")
    for name in ["overview", "sales", "products", "customers", "finance", "insights"]:
        t = time.perf_counter()
        r = client.get(f"/datasets/{dataset_id}/analytics/{name}{params}")
        print(
            f"  {name:10} {r.status_code}  {(time.perf_counter() - t) * 1000:7.0f} ms  {len(r.content) / 1024:6.1f} KB"
        )
    t = time.perf_counter()
    r = client.get(f"/datasets/{dataset_id}/records")
    print(
        f"  records    {r.status_code}  {(time.perf_counter() - t) * 1000:7.0f} ms  {len(r.content) / 1024:6.1f} KB  (gzip={r.headers.get('content-encoding')})"
    )


if __name__ == "__main__":
    main()
