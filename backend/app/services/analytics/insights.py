"""Automatic insights, ported from ``buildInsights`` (src/services/mock/analytics.mock.ts).

The frontend only renders insights – titles, summaries and evidence are produced here, already formatted.
"""

import numpy as np

from app.schemas.insight import Insight, InsightEvidence
from app.services.analytics.context import AnalyticsContext
from app.services.analytics.formatting import to_fixed
from app.services.analytics.metrics import (
    breakdown,
    fill_keys,
    margins_by_category,
    pct_change,
    product_performance,
    time_series,
    totals,
)
from app.services.analytics.slicing import Sliced

#: Minimum number of complete weeks before a week can be called "unusual", and the z-score that does it.
MIN_WEEKS_FOR_ANOMALY = 8
ANOMALY_Z = 2.0


def _evidence(*pairs: tuple[str, str]) -> list[InsightEvidence]:
    return [InsightEvidence(label=label, value=value) for label, value in pairs]


def build_insights(ctx: AnalyticsContext, sliced: Sliced) -> list[Insight]:
    f = ctx.formatters
    current, previous = sliced.current, sliced.previous
    if current.empty:
        return []
    cur = totals(current)
    prev = totals(previous) if previous is not None else None
    out: list[Insight] = []

    # ---- revenue vs previous period ---------------------------------------------------------------
    change = pct_change(cur.revenue, prev.revenue if prev else None)
    if prev is not None and change is not None:
        out.append(
            Insight(
                id="revenue-change",
                type="positive" if change >= 0 else "negative",
                metric="revenue",
                title=f"Revenue {'increased' if change >= 0 else 'decreased'} by {to_fixed(abs(change), 1)}% vs the previous period",
                summary=f"Revenue moved from {f.currency(prev.revenue)} to {f.currency(cur.revenue)} across comparable periods.",
                evidence=_evidence(
                    ("Current period", f.currency(cur.revenue)),
                    ("Previous period", f.currency(prev.revenue)),
                    ("Orders change", f.percent(pct_change(cur.orders, prev.orders) or 0, signed=True)),
                ),
            )
        )
    else:
        out.append(
            Insight(
                id="revenue-total",
                type="observation",
                metric="revenue",
                title=f"{f.currency(cur.revenue)} in revenue from {f.number(cur.orders)} orders",
                summary="Enable a comparison period to see how this compares with earlier performance.",
                evidence=_evidence(("Orders", f.number(cur.orders)), ("Average order value", f.currency(cur.aov))),
            )
        )

    # ---- categories -----------------------------------------------------------------------------------
    categories = breakdown(current, "category", previous)
    if categories:
        top = categories[0]
        out.append(
            Insight(
                id="top-category",
                type="observation",
                metric="category",
                title=f"{top.name} contributed {to_fixed(top.share, 1)}% of revenue",
                summary=f"It is the largest category, ahead of {categories[1].name if len(categories) > 1 else 'all others'}.",
                evidence=_evidence(
                    *[(c.name, f"{f.currency(c.value)} · {to_fixed(c.share, 1)}%") for c in categories[:3]]
                ),
            )
        )

    # ---- products ---------------------------------------------------------------------------------------
    products = product_performance(current, previous, has_cost=ctx.has_cost)
    top3 = sum(p.share for p in products[:3])
    if len(products) >= 5 and top3 > 40:
        out.append(
            Insight(
                id="concentration",
                type="recommendation",
                metric="product",
                title="Revenue is concentrated in a few products",
                summary="Review stock levels and promotion plans for the best sellers, and consider supporting mid-ranked products.",
                evidence=_evidence(
                    ("Top 3 products share", f"{to_fixed(top3, 1)}%"),
                    *[(p.name, f"{to_fixed(p.share, 1)}%") for p in products[:3]],
                ),
            )
        )
    if prev is not None:
        movers = [p for p in products if p.change is not None]
        if movers:
            best = max(movers, key=lambda p: p.change or 0)  # first of equals, like a stable sort
            worst = min(movers, key=lambda p: p.change or 0)
            if (best.change or 0) > 0:
                out.append(
                    Insight(
                        id="best-mover",
                        type="positive",
                        metric="product",
                        title=f"{best.name} grew {to_fixed(best.change or 0, 1)}% in revenue",
                        summary="The strongest improvement among all products versus the previous period.",
                        evidence=_evidence(("Revenue", f.currency(best.revenue)), ("Units", f.number(best.units))),
                    )
                )
            if (worst.change or 0) < 0:
                out.append(
                    Insight(
                        id="worst-mover",
                        type="negative",
                        metric="product",
                        title=f"{worst.name} declined {to_fixed(abs(worst.change or 0), 1)}% in revenue",
                        summary="The largest decline among products versus the previous period.",
                        evidence=_evidence(("Revenue", f.currency(worst.revenue)), ("Units", f.number(worst.units))),
                    )
                )

    # ---- unusual week (z-score over complete weeks) ---------------------------------------------------
    window = (sliced.range_from, sliced.range_to)
    weekly_all = time_series(current, "week", fill=fill_keys(window, ctx.span, "week"))
    last = len(weekly_all) - 1
    weekly = [p for i, p in enumerate(weekly_all) if 0 < i < last or len(weekly_all) < 3]  # drop partial edge weeks
    if len(weekly) >= MIN_WEEKS_FOR_ANOMALY:
        revenue = np.array([p.revenue for p in weekly])
        mean, sd = float(revenue.mean()), float(revenue.std())  # population sd, as in the original
        z = (revenue - mean) / sd if sd else np.zeros_like(revenue)
        at = int(np.argmax(np.abs(z)))
        if abs(z[at]) >= ANOMALY_Z and mean != 0:
            outlier, deviation = weekly[at], (revenue[at] - mean) / mean * 100
            out.append(
                Insight(
                    id="anomaly-week",
                    type="anomaly",
                    metric="revenue",
                    title=f"Unusual {'spike' if deviation > 0 else 'drop'} in the week of {f.date(outlier.date, 'long')}",
                    summary=(
                        f"Weekly revenue was {to_fixed(abs(deviation), 0)}% {'above' if deviation > 0 else 'below'} the typical week. "
                        "Check campaigns, outages or data-entry issues for that week."
                    ),
                    evidence=_evidence(
                        ("Revenue that week", f.currency(outlier.revenue)),
                        ("Typical week", f.currency(mean)),
                        ("Deviation", f"{to_fixed(float(z[at]), 1)} standard deviations"),
                    ),
                )
            )

    # ---- regions ----------------------------------------------------------------------------------------
    regions = breakdown(current, "region", previous)
    if len(regions) >= 3:
        even_share = 100 / len(regions)
        weakest = regions[-1]
        out.append(
            Insight(
                id="top-region",
                type="observation",
                metric="region",
                title=f"{regions[0].name} is the strongest region at {to_fixed(regions[0].share, 1)}% of revenue",
                summary="Regional share of total revenue across the selected period.",
                evidence=_evidence(*[(r.name, f"{to_fixed(r.share, 1)}%") for r in regions]),
            )
        )
        if weakest.share < even_share * 0.8:
            out.append(
                Insight(
                    id="weak-region",
                    type="recommendation",
                    metric="region",
                    title=f"Review growth opportunities in {weakest.name}",
                    summary="Its revenue share is well below an even split across regions.",
                    evidence=_evidence(
                        (f"{weakest.name} share", f"{to_fixed(weakest.share, 1)}%"),
                        ("Even-split benchmark", f"{to_fixed(even_share, 1)}%"),
                    ),
                )
            )

    # ---- margin -------------------------------------------------------------------------------------------
    if ctx.has_cost and cur.margin is not None:
        margins = margins_by_category(current).sort_values("margin", kind="stable")
        if not margins.empty:
            thinnest = margins.index[0]
            out.append(
                Insight(
                    id="low-margin",
                    type="recommendation",
                    metric="margin",
                    title=f"{thinnest} has the thinnest margin at {to_fixed(float(margins['margin'].iloc[0]), 1)}%",
                    summary="Review pricing or supplier costs for this category.",
                    evidence=_evidence(
                        *[(str(name), f"{to_fixed(float(m), 1)}%") for name, m in margins["margin"].items()]
                    ),
                )
            )

    # ---- customers --------------------------------------------------------------------------------------------
    if ctx.has_customers:
        # Distinct orders per customer (a customer with one multi-line order is not a repeat buyer).
        orders = current.dropna(subset=["customer"]).groupby("customer", observed=True)["order_code"].nunique()
        total = len(orders)
        if total > 0:
            repeat = int((orders > 1).sum())
            out.append(
                Insight(
                    id="repeat-rate",
                    type="observation",
                    metric="customers",
                    title=f"{to_fixed(repeat / total * 100, 1)}% of customers purchased more than once",
                    summary="Share of customers with at least two orders in the selected period.",
                    evidence=_evidence(("Customers", f.number(total)), ("Repeat customers", f.number(repeat))),
                )
            )
    return out
