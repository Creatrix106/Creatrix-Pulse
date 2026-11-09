"""Insight text and thresholds, checked against numbers worked out by hand (see the table in each test)."""

import datetime as dt
import math

import numpy as np
import pandas as pd
import pytest
from app.services.analytics.context import AnalyticsContext
from app.services.analytics.formatting import Formatters
from app.services.analytics.frames import build_frame
from app.services.analytics.insights import build_insights
from app.services.analytics.slicing import AnalyticsFilters, slice_frame


def make_frame(rows: list[tuple]) -> pd.DataFrame:
    """rows: (date, product, category, region, customer, revenue, cost[, order_id]) - quantity is always 1."""
    records = []
    for i, row in enumerate(rows, start=1):
        day, product, category, region, customer, revenue, cost, *rest = row
        records.append(
            {
                "row_number": i + 1,
                "order_date": pd.Timestamp(day),
                "order_id": rest[0] if rest else f"O{i}",
                "product": product,
                "category": category,
                "region": region,
                "customer": customer,
                "quantity": 1.0,
                "revenue": float(revenue),
                "cost": np.nan if cost is None else float(cost),
            }
        )
    frame = pd.DataFrame(records)
    frame["order_date"] = frame["order_date"].astype("datetime64[us]")
    for column in ("order_id", "product", "category", "region", "customer"):
        frame[column] = frame[column].astype("str")
    return frame


def insights_for(rows, filters=None, *, currency="INR", locale="en-IN", **caps):
    frame = build_frame(make_frame(rows))
    ctx = AnalyticsContext(
        frame,
        has_customers=caps.get("customers", frame.has_customer),
        has_cost=caps.get("cost", frame.has_cost),
        has_regions=caps.get("regions", frame.has_region),
        formatters=Formatters.create(currency, locale),
    )
    return {i.id: i for i in build_insights(ctx, slice_frame(frame, filters or AnalyticsFilters()))}, ctx


#            date        product category region customer revenue cost
FEB = [  # current period: 1 Feb - 28 Feb          (total 1,000, 8 orders)
    ("2026-02-03", "P1", "X", "R1", "C1", 200, 120),
    ("2026-02-10", "P1", "X", "R1", "C2", 200, 120),
    ("2026-02-05", "P2", "X", "R1", "C1", 100, 50),
    ("2026-02-12", "P2", "X", "R2", "C3", 200, 100),
    ("2026-02-14", "P3", "Y", "R2", "C4", 100, 80),
    ("2026-02-15", "P4", "Y", "R2", "C5", 80, 64),
    ("2026-02-20", "P5", "Z", "R3", "C6", 70, 63),
    ("2026-02-21", "P6", "Z", "R3", "C7", 50, 45),
]
JAN = [  # previous period: 4 Jan - 31 Jan         (total 900, 6 orders)
    ("2026-01-06", "P1", "X", "R1", "C1", 200, 120),
    ("2026-01-08", "P2", "X", "R1", "C2", 300, 150),
    ("2026-01-10", "P3", "Y", "R2", "C3", 100, 80),
    ("2026-01-12", "P4", "Y", "R2", "C4", 100, 80),
    ("2026-01-20", "P5", "Z", "R3", "C5", 100, 90),
    ("2026-01-25", "P6", "Z", "R3", "C6", 100, 90),
]
FEB_VS_JAN = AnalyticsFilters(
    date_preset="custom", date_from=dt.date(2026, 2, 1), date_to=dt.date(2026, 2, 28), comparison="previous_period"
)


def test_every_insight_for_a_period_over_period_comparison():
    found, _ = insights_for(JAN + FEB, FEB_VS_JAN)
    assert list(found) == [
        "revenue-change",
        "top-category",
        "concentration",
        "best-mover",
        "worst-mover",
        "top-region",
        "weak-region",
        "low-margin",
        "repeat-rate",
    ]  # fmt: skip (order = the order of the original generator)

    # revenue: 900 -> 1,000 = +11.11%; orders 6 -> 8 = +33.3%
    rev = found["revenue-change"]
    assert rev.type == "positive" and rev.metric == "revenue"
    assert rev.title == "Revenue increased by 11.1% vs the previous period"
    assert rev.summary == "Revenue moved from ₹900 to ₹1,000 across comparable periods."
    assert [(e.label, e.value) for e in rev.evidence] == [
        ("Current period", "₹1,000"), ("Previous period", "₹900"), ("Orders change", "+33.3%"),
    ]  # fmt: skip

    # categories: X = 200+200+100+200 = 700 (70%), Y = 180, Z = 120
    cat = found["top-category"]
    assert cat.title == "X contributed 70.0% of revenue"
    assert cat.summary == "It is the largest category, ahead of Y."
    assert [(e.label, e.value) for e in cat.evidence] == [
        ("X", "₹700 · 70.0%"),
        ("Y", "₹180 · 18.0%"),
        ("Z", "₹120 · 12.0%"),
    ]

    # top 3 products = 400 + 300 + 100 = 80% of revenue (> 40%) across 6 products (>= 5)
    conc = found["concentration"]
    assert conc.type == "recommendation"
    assert [(e.label, e.value) for e in conc.evidence] == [
        ("Top 3 products share", "80.0%"), ("P1", "40.0%"), ("P2", "30.0%"), ("P3", "10.0%"),
    ]  # fmt: skip

    # movers: P1 200 -> 400 = +100%; P6 100 -> 50 = -50%
    assert found["best-mover"].title == "P1 grew 100.0% in revenue"
    assert [(e.label, e.value) for e in found["best-mover"].evidence] == [("Revenue", "₹400"), ("Units", "2")]
    assert found["worst-mover"].title == "P6 declined 50.0% in revenue"
    assert found["worst-mover"].type == "negative"

    # regions: R1 500 (50%), R2 380 (38%), R3 120 (12%); an even split would be 33.3%, and 12 < 0.8 * 33.3
    assert found["top-region"].title == "R1 is the strongest region at 50.0% of revenue"
    assert [(e.label, e.value) for e in found["top-region"].evidence] == [
        ("R1", "50.0%"),
        ("R2", "38.0%"),
        ("R3", "12.0%"),
    ]
    weak = found["weak-region"]
    assert weak.title == "Review growth opportunities in R3"
    assert [(e.label, e.value) for e in weak.evidence] == [("R3 share", "12.0%"), ("Even-split benchmark", "33.3%")]

    # margins: X (700-390)/700 = 44.3%, Y (180-144)/180 = 20.0%, Z (120-108)/120 = 10.0%
    margin = found["low-margin"]
    assert margin.title == "Z has the thinnest margin at 10.0%"
    assert [(e.label, e.value) for e in margin.evidence] == [("Z", "10.0%"), ("Y", "20.0%"), ("X", "44.3%")]

    # customers: 7 buyers, only C1 ordered twice -> 1/7 = 14.3%
    repeat = found["repeat-rate"]
    assert repeat.title == "14.3% of customers purchased more than once"
    assert [(e.label, e.value) for e in repeat.evidence] == [("Customers", "7"), ("Repeat customers", "1")]


def test_a_decline_is_reported_as_negative():
    shrunk = [(d, p, c, r, cu, rev / 2, cost / 2) for d, p, c, r, cu, rev, cost in FEB]
    found, _ = insights_for(JAN + shrunk, FEB_VS_JAN)
    assert found["revenue-change"].type == "negative"
    assert found["revenue-change"].title == "Revenue decreased by 44.4% vs the previous period"  # 500 vs 900


def test_without_a_comparison_the_first_insight_is_a_plain_total():
    found, _ = insights_for(FEB)
    assert "revenue-change" not in found
    total = found["revenue-total"]
    assert total.type == "observation"
    assert total.title == "₹1,000 in revenue from 8 orders"
    assert [(e.label, e.value) for e in total.evidence] == [("Orders", "8"), ("Average order value", "₹125")]
    assert not {"best-mover", "worst-mover"} & set(found)  # movers need a previous period


def test_insights_follow_the_requested_currency_and_locale():
    found, _ = insights_for(JAN + FEB, FEB_VS_JAN, currency="USD", locale="en-US")
    assert found["revenue-change"].summary == "Revenue moved from $900 to $1,000 across comparable periods."
    found, _ = insights_for(JAN + FEB, FEB_VS_JAN, currency="EUR", locale="de-DE")
    assert found["revenue-change"].summary == "Revenue moved from 900\xa0€ to 1.000\xa0€ across comparable periods."


def test_nothing_to_say_about_an_empty_selection():
    found, _ = insights_for(FEB, AnalyticsFilters(categories=("Nope",)))
    assert found == {}


def test_concentration_needs_five_products_and_a_top_three_above_forty_percent():
    ten_equal = [("2026-02-01", f"P{i}", "X", "R1", f"C{i}", 100, 50) for i in range(10)]  # top 3 = 30%
    assert "concentration" not in insights_for(ten_equal)[0]
    four = [("2026-02-01", f"P{i}", "X", "R1", f"C{i}", 100, 50) for i in range(4)]  # top 3 = 75% but only 4 products
    assert "concentration" not in insights_for(four)[0]


def test_region_insights_need_three_regions_and_a_clearly_weak_one():
    two = [("2026-02-01", "P", "X", r, "C", 100, 50) for r in ("R1", "R2")]
    found = insights_for(two)[0]
    assert "top-region" not in found and "weak-region" not in found
    balanced = [("2026-02-01", "P", "X", r, "C", 100, 50) for r in ("R1", "R2", "R3")]
    found = insights_for(balanced)[0]
    assert "top-region" in found and "weak-region" not in found  # 33.3% each: nobody is below 80% of an even split


def test_margin_and_customer_insights_only_exist_with_the_data_they_need():
    no_cost = [(d, p, c, r, cu, rev, None) for d, p, c, r, cu, rev, _ in FEB]
    found, ctx = insights_for(no_cost)
    assert not ctx.has_cost and "low-margin" not in found
    no_customers = [(d, p, c, r, None, rev, cost) for d, p, c, r, _, rev, cost in FEB]
    found, ctx = insights_for(no_customers)
    assert not ctx.has_customers and "repeat-rate" not in found


def test_multi_line_orders_do_not_count_as_repeat_customers():
    lines = [("2026-02-01", f"P{i}", "X", "R1", "C1", 10, 5, "ONE-ORDER") for i in range(3)]  # 3 lines, 1 order
    lines += [("2026-02-02", "P", "X", "R1", "C2", 10, 5, "A"), ("2026-02-03", "P", "X", "R1", "C2", 10, 5, "B")]
    found, _ = insights_for(lines)
    assert found["repeat-rate"].title == "50.0% of customers purchased more than once"  # only C2 (1 of 2)


def anomaly_rows(spike_week: int | None, weeks: int = 12, base: int = 1000, spike: int = 6000):
    """One row every Wednesday, a Sunday before the first full week and a Monday after the last (partial edge weeks)."""
    rows = [("2026-01-04", "P", "X", "R1", "C", 1, 0)]  # Sunday: belongs to the week that starts Mon 29 Dec
    wednesday = dt.date(2026, 1, 7)
    for week in range(weeks):
        revenue = spike if week == spike_week else base
        rows.append(((wednesday + dt.timedelta(weeks=week)).isoformat(), "P", "X", "R1", "C", revenue, 0))
    rows.append(
        ((wednesday + dt.timedelta(weeks=weeks, days=-2)).isoformat(), "P", "X", "R1", "C", 1, 0)
    )  # the Monday after the last week
    return rows


def test_a_week_far_from_the_typical_week_is_flagged_with_its_z_score():
    found, _ = insights_for(anomaly_rows(spike_week=6))  # the 7th Wednesday = 18 Feb 2026, week of Mon 16 Feb
    anomaly = found["anomaly-week"]
    assert anomaly.type == "anomaly"
    assert anomaly.title == "Unusual spike in the week of 16 Feb 2026"
    # 11 weeks of 1,000 and one of 6,000: mean = 17,000/12 = 1,416.67, deviation = +323.5%, z = sqrt(n - 1) = 3.3
    assert anomaly.summary.startswith("Weekly revenue was 324% above the typical week.")
    assert [(e.label, e.value) for e in anomaly.evidence] == [
        ("Revenue that week", "₹6,000"), ("Typical week", "₹1,417"), ("Deviation", f"{math.sqrt(11):.1f} standard deviations"),
    ]  # fmt: skip


def test_a_dip_is_called_a_drop():
    found, _ = insights_for(anomaly_rows(spike_week=3, spike=0))  # a week with no sales at all
    assert found["anomaly-week"].title.startswith("Unusual drop in the week of")
    assert "below the typical week" in found["anomaly-week"].summary


def test_steady_sales_or_too_little_history_are_not_anomalies():
    assert "anomaly-week" not in insights_for(anomaly_rows(spike_week=None))[0]  # perfectly flat
    assert "anomaly-week" not in insights_for(anomaly_rows(spike_week=3, weeks=7))[0]  # < 8 complete weeks


def test_the_gaps_between_sales_count_as_zero_weeks_for_anomaly_detection():
    rows = anomaly_rows(spike_week=None)
    rows = [r for i, r in enumerate(rows) if i != 5]  # nothing sold in one whole week
    found, _ = insights_for(rows)
    assert found["anomaly-week"].title.startswith("Unusual drop in the week of")


@pytest.mark.parametrize("value", [0.25, 2.5, 1.005])
def test_exact_ties_round_like_javascript(value):
    # guards the reason insights use their own rounding rather than Python's: 0.25 -> "0.3", 2.5 -> "3"
    from app.services.analytics.formatting import to_fixed

    expected = {0.25: ("0.3", 1), 2.5: ("3", 0), 1.005: ("1.00", 2)}[value]
    assert to_fixed(value, expected[1]) == expected[0]
