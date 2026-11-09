"""Naive, loop-based reference implementation of the dashboard maths (the test oracle).

A deliberately literal port of the original TypeScript engine (frontend src/services/mock/engine.ts and
analytics.mock.ts) using plain dicts and ``datetime`` – no pandas, no numpy, no vectorisation – so that the
pandas engine in ``app/`` is checked against an independently written implementation. Calendar logic
(Monday weeks, month starts) uses ``date.weekday()`` / ``date.replace`` rather than numpy datetime math.

Differences from the TS original mirror the documented, intentional ones in the production code:
zero-filled series and distinct-order counting.
"""

from collections import defaultdict
from datetime import date, timedelta

import pandas as pd


def to_rows(frame: pd.DataFrame) -> list[dict]:
    rows = []
    for r in frame.itertuples(index=False):
        rows.append(
            {
                "order": r.order_id if isinstance(r.order_id, str) else f"row-{r.row_number}",
                "date": r.order_date.date(),
                "product": r.product,
                "category": r.category if isinstance(r.category, str) else None,
                "region": r.region if isinstance(r.region, str) else None,
                "customer": r.customer if isinstance(r.customer, str) else None,
                "qty": float(r.quantity),
                "revenue": float(r.revenue),
                "cost": None if pd.isna(r.cost) else float(r.cost),
            }
        )
    rows.sort(key=lambda x: x["date"])
    return rows


def pct_change(cur, prev):
    return None if prev is None or prev == 0 else (cur - prev) / prev * 100


def bucket(d: date, group_by: str) -> date:
    if group_by == "day":
        return d
    if group_by == "month":
        return d.replace(day=1)
    return d - timedelta(days=d.weekday())


def in_scope(r, f):
    return (not f["categories"] or r["category"] in f["categories"]) and (
        not f["regions"] or (r["region"] is not None and r["region"] in f["regions"])
    )


def slice_rows(rows, f):
    lo, hi = rows[0]["date"], rows[-1]["date"]
    start, end = lo, hi
    days = {"last_30d": 30, "last_90d": 90, "last_180d": 180}.get(f["date_preset"])
    if days:
        start = hi - timedelta(days=days - 1)
    elif f["date_preset"] == "ytd":
        start = date(hi.year, 1, 1)
    elif f["date_preset"] == "custom" and f["date_from"] and f["date_to"]:
        start, end = f["date_from"], f["date_to"]
    scoped = [r for r in rows if in_scope(r, f)]
    current = [r for r in scoped if start <= r["date"] <= end]
    previous = None
    if f["comparison"] == "previous_period" and f["date_preset"] != "all":
        length = (end - start).days + 1
        p_end, p_start = start - timedelta(days=1), start - timedelta(days=length)
        prev_rows = [r for r in scoped if p_start <= r["date"] <= p_end]
        previous = prev_rows or None
    return {"current": current, "previous": previous, "from": start, "to": end, "scoped": scoped, "span": (lo, hi)}


def totals(rows):
    revenue = sum(r["revenue"] for r in rows)
    orders = len({r["order"] for r in rows})
    units = sum(r["qty"] for r in rows)
    has_cost = bool(rows) and all(r["cost"] is not None for r in rows)
    cost = sum(r["cost"] for r in rows) if has_cost else None
    profit = None if cost is None else revenue - cost
    return {
        "revenue": revenue,
        "orders": orders,
        "units": units,
        "aov": revenue / orders if orders else 0,
        "cost": cost,
        "profit": profit,
        "margin": None if profit is None or revenue == 0 else profit / revenue * 100,
    }


def bucket_keys(start: date, end: date, span, group_by):
    lo, hi = max(start, span[0]), min(end, span[1])
    keys, d = [], lo
    while d <= hi:
        k = bucket(d, group_by)
        if not keys or keys[-1] != k:
            keys.append(k)
        d += timedelta(days=1)
    return keys


def time_series(rows, group_by, window, span, has_cost):
    if not rows:
        return []
    groups = defaultdict(list)
    for r in rows:
        groups[bucket(r["date"], group_by)].append(r)
    out = []
    for key in bucket_keys(window[0], window[1], span, group_by):
        t = totals(groups.get(key, []))
        point = {
            "date": key,
            "revenue": t["revenue"],
            "orders": t["orders"],
            "units": t["units"],
            "aov": int(t["aov"] + 0.5) if t["aov"] >= 0 else -int(-t["aov"] + 0.5),
        }
        if has_cost:
            cost = sum(r["cost"] for r in groups.get(key, []))
            point["cost"], point["profit"] = cost, t["revenue"] - cost
            if t["revenue"] != 0:
                point["margin"] = (t["revenue"] - cost) / t["revenue"] * 100
        out.append(point)
    return out


def breakdown(rows, key, previous):
    def sums(lst):
        m = defaultdict(lambda: [0.0, 0.0])
        for r in lst:
            if r[key] is None:
                continue
            m[r[key]][0] += r["revenue"]
            m[r[key]][1] += r["qty"]
        return m

    cur = sums(rows)
    prev = sums(previous) if previous else None
    total = sum(v[0] for v in cur.values())
    items = [
        {
            "name": n,
            "value": v[0],
            "share": v[0] / total * 100 if total else 0,
            "secondary": v[1],
            "change": pct_change(v[0], prev[n][0]) if prev and n in prev else None,
        }
        for n, v in cur.items()
    ]
    return sorted(items, key=lambda i: (-i["value"], i["name"]))


def products(rows, previous):
    def group(lst):
        m = {}
        for r in lst:
            e = m.setdefault(
                r["product"], {"revenue": 0.0, "units": 0.0, "orders": set(), "cost": 0.0, "category": r["category"]}
            )
            e["revenue"] += r["revenue"]
            e["units"] += r["qty"]
            e["orders"].add(r["order"])
            e["cost"] += r["cost"] or 0
            if e["category"] is None:
                e["category"] = r["category"]
        return m

    cur = group(rows)
    prev = group(previous) if previous else None
    total = sum(v["revenue"] for v in cur.values())
    out = [
        {
            "name": n,
            "category": v["category"] or "Uncategorized",
            "revenue": v["revenue"],
            "units": v["units"],
            "orders": len(v["orders"]),
            "share": v["revenue"] / total * 100 if total else 0,
            "change": pct_change(v["revenue"], prev[n]["revenue"]) if prev and n in prev else None,
            "margin": (v["revenue"] - v["cost"]) / v["revenue"] * 100 if v["revenue"] else None,
        }
        for n, v in cur.items()
    ]
    return sorted(out, key=lambda p: (-p["revenue"], p["name"]))


def customers(s, group_by, has_regions):
    cur = [r for r in s["current"] if r["customer"]]
    prev = [r for r in s["previous"] if r["customer"]] if s["previous"] else None
    first = {}
    for r in s["scoped"]:  # rows are date-sorted
        if r["customer"] and r["customer"] not in first:
            first[r["customer"]] = r["date"]

    per = defaultdict(lambda: {"orders": set(), "revenue": 0.0})
    for r in cur:
        per[r["customer"]]["orders"].add(r["order"])
        per[r["customer"]]["revenue"] += r["revenue"]
    total = len(per)
    new = sum(1 for c in per if first[c] >= s["from"])
    revenue = sum(r["revenue"] for r in cur)
    per_customer = revenue / total if total else 0
    prev_ids = {r["customer"] for r in prev} if prev else None
    prev_per = sum(r["revenue"] for r in prev) / len(prev_ids) if prev and prev_ids else None

    pairs = defaultdict(set)
    for r in cur:
        pairs[bucket(r["date"], group_by)].add(r["customer"])
    nvr = []
    for key in bucket_keys(s["from"], s["to"], s["span"], group_by):
        ids = pairs.get(key, set())
        fresh = sum(1 for c in ids if bucket(first[c], group_by) == key)
        nvr.append({"date": key, "new": fresh, "returning": len(ids) - fresh})

    bins = [0] * 6
    seg = {"Champions": [0, 0.0], "Loyal": [0, 0.0], "Returning": [0, 0.0], "One-time": [0, 0.0]}
    for v in per.values():
        n = len(v["orders"])
        bins[min(n, 6) - 1] += 1
        name = "Champions" if n >= 6 else "Loyal" if n >= 3 else "Returning" if n == 2 else "One-time"
        seg[name][0] += 1
        seg[name][1] += v["revenue"]
    dist = defaultdict(set)
    if has_regions:
        for r in cur:
            if r["region"]:
                dist[r["region"]].add(r["customer"])
    distribution = sorted(
        ({"name": k, "value": len(v), "share": len(v) / total * 100} for k, v in dist.items()),
        key=lambda i: (-i["value"], i["name"]),
    )
    return {
        "total": total,
        "new": new,
        "rpc": per_customer,
        "rpc_change": pct_change(per_customer, prev_per),
        "customers_change": pct_change(total, len(prev_ids) if prev_ids is not None else None),
        "nvr": nvr,
        "bins": bins,
        "segments": {
            k: {"customers": v[0], "revenue": v[1], "share": v[0] / total * 100 if total else 0} for k, v in seg.items()
        },
        "distribution": distribution,
    }


def margins_by_category(rows):
    m = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        if r["category"] is None:
            continue
        m[r["category"]][0] += r["revenue"]
        m[r["category"]][1] += r["cost"] or 0
    return {
        n: {"revenue": v[0], "cost": v[1], "profit": v[0] - v[1], "margin": (v[0] - v[1]) / v[0] * 100 if v[0] else 0}
        for n, v in m.items()
    }
