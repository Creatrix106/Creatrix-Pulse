"""Deterministic synthetic sales data for tests (cleaned-frame layout, see ingestion.cleaner.CleanedData)."""

import numpy as np
import pandas as pd

PRODUCTS = [
    ("Earbuds Pro", "Electronics", 6499, 0.62),
    ("Smartwatch", "Electronics", 8999, 0.66),
    ("Speaker", "Electronics", 4299, 0.60),
    ("Everyday Tee", "Apparel", 799, 0.38),
    ("Trail Jacket", "Apparel", 3499, 0.47),
    ("Joggers", "Apparel", 1499, 0.42),
    ("Table Lamp", "Home & Living", 1899, 0.50),
    ("Throw Blanket", "Home & Living", 1299, 0.44),
    ("Glow Serum", "Personal Care", 999, 0.30),
    ("Shampoo", "Personal Care", 449, 0.34),
]
REGIONS = ["North", "South", "West", "East"]


def make_rows(
    days: int = 300,
    seed: int = 7,
    *,
    start: str = "2026-01-01",
    customers: bool = True,
    cost: bool = True,
    regions: bool = True,
    categories: bool = True,
    gap_rate: float = 0.08,
    n_customers: int = 400,
) -> pd.DataFrame:
    """Orders with several lines each, days without any sales, a campaign spike and an outage dip."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=days, freq="D")
    rows: list[dict] = []
    order_no, row_no = 10_000, 2
    customer_region = {c: REGIONS[int(rng.integers(0, 4))] for c in range(n_customers)}
    for i, day in enumerate(dates):
        if rng.random() < gap_rate:  # no sales that day
            continue
        factor = 4 + 3 * i / days
        if days > 250 and 215 <= i <= 217:
            factor *= 3.2  # campaign spike
        if days > 250 and 100 <= i <= 102:
            factor *= 0.3  # outage
        for _ in range(max(0, int(rng.poisson(factor)))):
            order_no += 1
            cust = int(rng.integers(0, n_customers))
            for _line in range(int(rng.integers(1, 4))):  # 1-3 lines per order
                name, cat, price, cost_ratio = PRODUCTS[int(rng.integers(0, len(PRODUCTS)))]
                qty = int(rng.integers(1, 4))
                revenue = round(price * qty * float(rng.uniform(0.92, 1.04)), 2)
                rows.append(
                    {
                        "row_number": row_no,
                        "order_date": day,
                        "order_id": f"ORD-{order_no}",
                        "product": name,
                        "category": cat if categories else None,
                        "region": customer_region[cust] if regions else None,
                        "customer": f"C-{cust:04d}" if customers else None,
                        "quantity": float(qty),
                        "revenue": revenue,
                        "cost": round(revenue * cost_ratio * float(rng.uniform(0.96, 1.04)), 2) if cost else np.nan,
                    }
                )
                row_no += 1
    frame = pd.DataFrame(rows)
    frame["order_date"] = frame["order_date"].astype("datetime64[us]")
    for column in ("order_id", "product", "category", "region", "customer"):
        frame[column] = frame[column].astype("str")
    frame["row_number"] = frame["row_number"].astype("int32")
    return frame
