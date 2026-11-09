"""Differential tests: the pandas engine must agree with the naive reference implementation
(tests/reference_engine.py) on every number, for many random filter combinations and dataset shapes."""

import datetime as dt
import random

import pytest
from app.services.analytics import dashboards as D
from app.services.analytics.context import AnalyticsContext
from app.services.analytics.formatting import Formatters
from app.services.analytics.frames import build_frame
from app.services.analytics.slicing import AnalyticsFilters, slice_frame

from tests import reference_engine as ref
from tests.factories import make_rows

MONEY = {"abs": 0.011}  # outputs are rounded to 2 decimals
PCT = {"abs": 2e-4}  # ... and ratios/percentages to 4

SHAPES = {
    "full": dict(),
    "no_cost": dict(cost=False),
    "no_customers": dict(customers=False),
    "no_regions": dict(regions=False),
    "no_categories": dict(categories=False),
}


@pytest.fixture(scope="module", params=list(SHAPES))
def world(request):
    frame_rows = make_rows(days=300, seed=11, **SHAPES[request.param])
    frame = build_frame(frame_rows)
    caps = dict(
        has_customers=bool(frame.has_customer), has_cost=bool(frame.has_cost), has_regions=bool(frame.has_region)
    )
    ctx = AnalyticsContext(frame, formatters=Formatters.create("INR", "en-IN"), **caps)
    return request.param, ctx, ref.to_rows(frame_rows), caps


def random_filters(rng: random.Random, cats: list[str], regs: list[str]) -> dict:
    preset = rng.choice(["all", "last_30d", "last_90d", "last_180d", "ytd", "custom", "custom"])
    start = dt.date(2026, 1, 1) + dt.timedelta(days=rng.randint(0, 200))
    return dict(
        date_preset=preset,
        date_from=start if preset == "custom" else None,
        date_to=start + dt.timedelta(days=rng.randint(10, 120)) if preset == "custom" else None,
        comparison=rng.choice(["none", "previous_period", "previous_period"]),
        group_by=rng.choice(["day", "week", "month"]),
        categories=tuple(rng.sample(cats, rng.randint(0, min(2, len(cats))))) if cats else (),
        regions=tuple(rng.sample(regs, rng.randint(0, min(2, len(regs))))) if regs else (),
    )


def check_series(mine, theirs, has_cost):
    assert [str(p.date) for p in mine] == [str(p["date"]) for p in theirs]
    for m, t in zip(mine, theirs, strict=True):
        assert m.revenue == pytest.approx(t["revenue"], **MONEY)
        assert m.orders == t["orders"]
        assert m.units == pytest.approx(t["units"], abs=1e-3)
        assert m.aov == t["aov"] or abs(m.aov - t["aov"]) <= 1  # Math.round vs rounding of the 2-decimal revenue
        if has_cost:
            assert m.cost == pytest.approx(t["cost"], **MONEY)
            assert m.profit == pytest.approx(t["profit"], **MONEY)
            assert (m.margin is None) == ("margin" not in t)
            if m.margin is not None:
                assert m.margin == pytest.approx(t["margin"], abs=0.051)  # one decimal
        else:
            assert m.cost is None and m.profit is None and m.margin is None


def check_breakdown(mine, theirs):
    assert [b.name for b in mine] == [b["name"] for b in theirs]
    for m, t in zip(mine, theirs, strict=True):
        assert m.value == pytest.approx(t["value"], **MONEY)
        assert m.share == pytest.approx(t["share"], **PCT)
        assert m.secondary == pytest.approx(t["secondary"], abs=1e-3)
        if t["change"] is None:
            assert m.change is None
        else:
            assert m.change == pytest.approx(t["change"], **PCT)


@pytest.mark.parametrize("seed", range(40))
def test_dashboards_match_reference(world, seed):
    shape, ctx, rows, caps = world
    rng = random.Random(seed * 7919 + len(shape))
    cats = sorted({r["category"] for r in rows if r["category"]})
    regs = sorted({r["region"] for r in rows if r["region"]})
    f = random_filters(rng, cats, regs)
    flt = AnalyticsFilters(**f)
    s = slice_frame(ctx.frame, flt)
    r = ref.slice_rows(rows, f)

    # ---- slice -----------------------------------------------------------------------------------
    assert (s.range_from, s.range_to) == (r["from"], r["to"])
    assert len(s.current) == len(r["current"])
    assert (None if s.previous is None else len(s.previous)) == (None if r["previous"] is None else len(r["previous"]))

    cur, prev = ref.totals(r["current"]), (ref.totals(r["previous"]) if r["previous"] else None)

    # ---- overview / sales ------------------------------------------------------------------------
    ov, sales, prod = D.overview(ctx, s), D.sales(ctx, s), D.products(ctx, s)
    kpis = {k.id: k for k in ov.kpis}
    for key in ("revenue", "orders", "units", "aov"):
        assert kpis[key].value == pytest.approx(cur[key], **MONEY)
        expected = ref.pct_change(cur[key], prev[key] if prev else None)
        assert (kpis[key].change is None) == (expected is None), key
        if expected is not None:
            assert kpis[key].change == pytest.approx(expected, **PCT)
    if caps["has_cost"] and r["current"]:
        assert kpis["profit"].value == pytest.approx(cur["profit"], **MONEY)
        assert kpis["margin"].value == pytest.approx(cur["margin"], **PCT)
        if prev and prev["margin"] is not None:
            assert kpis["margin"].change == pytest.approx(cur["margin"] - prev["margin"], **PCT)
    else:
        assert "profit" not in kpis and "margin" not in kpis

    window = (r["from"], r["to"])
    group_by = f["group_by"]
    check_series(
        ov.revenue_trend,
        ref.time_series(r["current"], group_by, window, r["span"], caps["has_cost"] and bool(r["current"])),
        caps["has_cost"] and bool(r["current"]),
    )
    if r["previous"]:
        length = (r["to"] - r["from"]).days + 1
        pwin = (r["from"] - dt.timedelta(days=length), r["from"] - dt.timedelta(days=1))
        check_series(
            sales.previous_trend,
            ref.time_series(r["previous"], group_by, pwin, (pwin[0], r["span"][1]), caps["has_cost"]),
            caps["has_cost"],
        )
    else:
        assert sales.previous_trend is None

    check_breakdown(ov.categories, ref.breakdown(r["current"], "category", r["previous"]))
    check_breakdown(ov.regions, ref.breakdown(r["current"], "region", r["previous"]))
    assert sales.category_names == [c.name for c in ov.categories]

    # category trend: values per (zero-filled) bucket
    ref_bucket = {}
    for row in r["current"]:
        if row["category"]:
            ref_bucket.setdefault(ref.bucket(row["date"], group_by), {}).setdefault(row["category"], 0.0)
            ref_bucket[ref.bucket(row["date"], group_by)][row["category"]] += row["revenue"]
    for point in sales.category_trend:
        expected = ref_bucket.get(point.date, {})
        assert point.values.keys() == expected.keys()
        for k, v in point.values.items():
            assert v == pytest.approx(expected[k], **MONEY)
    assert {p.date for p in sales.category_trend} >= set(ref_bucket)

    # ---- products --------------------------------------------------------------------------------------
    expected_products = ref.products(r["current"], r["previous"])
    assert [p.name for p in prod.all] == [p["name"] for p in expected_products]
    for m, t in zip(prod.all, expected_products, strict=True):
        assert (m.revenue, m.units, m.orders) == (
            pytest.approx(t["revenue"], **MONEY),
            pytest.approx(t["units"]),
            t["orders"],
        )
        assert m.share == pytest.approx(t["share"], **PCT)
        assert m.category == t["category"]
        assert (m.change is None) == (t["change"] is None)
        if t["change"] is not None:
            assert m.change == pytest.approx(t["change"], **PCT)
        if caps["has_cost"]:
            assert m.margin == pytest.approx(t["margin"], **PCT)
        else:
            assert m.margin is None
    assert [p.name for p in prod.top] == [p["name"] for p in expected_products[:5]]
    assert [p.name for p in prod.low] == [p["name"] for p in reversed(expected_products)][:5]

    # ---- customers -------------------------------------------------------------------------------------
    cust = D.customers(ctx, s)
    if not caps["has_customers"]:
        assert cust.available is False
    else:
        c = ref.customers(r, group_by, caps["has_regions"])
        d = {k.id: k for k in cust.data.kpis}
        assert d["customers"].value == c["total"]
        assert d["new"].value == c["new"] and d["returning"].value == c["total"] - c["new"]
        assert d["rpc"].value == pytest.approx(c["rpc"], **MONEY)
        for key, expected in (("customers", c["customers_change"]), ("rpc", c["rpc_change"])):
            assert (d[key].change is None) == (expected is None), key
            if expected is not None:
                assert d[key].change == pytest.approx(expected, **PCT)
        assert [(str(p.date), p.new_customers, p.returning_customers) for p in cust.data.new_vs_returning] == [
            (str(x["date"]), x["new"], x["returning"]) for x in c["nvr"]
        ] or not r["current"]
        assert [b.count for b in cust.data.frequency] == c["bins"]
        for seg in cust.data.segments:
            e = c["segments"][seg.name]
            assert (seg.customers, seg.revenue, seg.share) == (
                e["customers"],
                pytest.approx(e["revenue"], **MONEY),
                pytest.approx(e["share"], **PCT),
            )
        assert [(b.name, b.value) for b in cust.data.distribution] == [
            (x["name"], x["value"]) for x in c["distribution"]
        ]

    # ---- finance ---------------------------------------------------------------------------------------
    fin = D.finance(ctx, s)
    if not caps["has_cost"]:
        assert fin.available is False
    else:
        assert fin.available
        margins = ref.margins_by_category(r["current"])
        total_profit = sum(m["profit"] for m in margins.values())
        got = {m.name: m for m in fin.data.category_margins}
        assert got.keys() == margins.keys()
        for name, m in margins.items():
            assert got[name].value == pytest.approx(m["margin"], abs=0.051)
            assert got[name].secondary == pytest.approx(m["profit"], **MONEY)
            if total_profit:
                assert got[name].share == pytest.approx(m["profit"] / total_profit * 100, **PCT)
        values = [m.value for m in fin.data.category_margins]
        assert values == sorted(values, reverse=True)
        fk = {k.id: k for k in fin.data.kpis}
        assert fk["cost"].value == pytest.approx(cur["cost"] or 0, **MONEY) and fk["cost"].inverse is True
