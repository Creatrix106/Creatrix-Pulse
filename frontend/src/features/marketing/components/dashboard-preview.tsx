"use client";

import { AreaChart, BarChart, DonutChart } from "@/components/charts";
import { LogoMark } from "@/components/ui/logo";
import { createFormatters } from "@/utils/format";
import { cn } from "@/utils/cn";
import { previewCategories, previewKpis, previewNav, previewProducts, previewRegions, previewTrend } from "../preview-data";
import { TrendIndicator } from "@/components/dashboard/trend-indicator";

const f = createFormatters({ currency: "INR", locale: "en-IN" });

interface DashboardPreviewProps {
  /** "compact" is used in the hero, "full" in the showcase section. */
  variant?: "compact" | "full";
  className?: string;
}

/** Static illustration of the product UI built from the real chart components. */
export function DashboardPreview({ variant = "compact", className }: DashboardPreviewProps) {
  const full = variant === "full";
  const kpis = full ? previewKpis : previewKpis.slice(0, 3);

  return (
    <div className={cn("overflow-hidden rounded-xl border border-border bg-surface shadow-modal", className)} role="img" aria-label="Preview of the Creatrix Pulse analytics dashboard">
      <div className="flex">
        <aside className="hidden w-36 shrink-0 bg-sidebar p-3 text-sidebar-fg sm:block">
          <div className="mb-4 flex items-center gap-1.5 text-xs font-semibold text-white"><LogoMark className="size-4 text-white" /> Creatrix Pulse</div>
          <ul className="space-y-1 text-[11px]">
            {previewNav.slice(0, full ? 6 : 6).map((item, i) => (
              <li key={item} className={cn("rounded px-2 py-1.5", i === 0 ? "bg-sidebar-active text-white" : "text-sidebar-fg")}>{item}</li>
            ))}
          </ul>
        </aside>

        <div className="min-w-0 flex-1 bg-surface p-3 sm:p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-emphasis">Overview</p>
            <span className="rounded border border-border px-2 py-1 text-[10px] text-muted">Jan 1, 2026 – Oct 31, 2026</span>
          </div>

          <div className={cn("grid gap-2", full ? "grid-cols-2 sm:grid-cols-5" : "grid-cols-3")}>
            {kpis.map((k) => (
              <div key={k.id} className="rounded-md border border-border bg-surface p-2">
                <p className="text-[10px] text-muted">{k.label}</p>
                <p className="tabular text-sm font-semibold text-emphasis">{k.format === "percent" ? f.percent(k.value, { digits: 2 }) : f.kpi(k.value, k.format)}</p>
                {k.change != null && <TrendIndicator value={k.change} suffix="%" className="text-[10px]" />}
              </div>
            ))}
          </div>

          <div className={cn("mt-3 grid gap-3", full ? "lg:grid-cols-5" : "lg:grid-cols-5")}>
            <div className="rounded-md border border-border p-3 lg:col-span-3">
              <p className="mb-1 text-xs font-semibold text-emphasis">Revenue Trend</p>
              <AreaChart data={previewTrend} xKey="date" series={[{ key: "revenue", label: "Revenue" }]} height={full ? 170 : 150} valueFormatter={(v) => f.currency(v, { compact: true })} xFormatter={(v) => f.period(v, "month")} tooltipLabelFormatter={(v) => f.period(v, "month", "long")} ariaLabel="Revenue trend preview" />
            </div>
            <div className="space-y-3 lg:col-span-2">
              <div className="rounded-md border border-border p-3">
                <p className="mb-2 text-xs font-semibold text-emphasis">Top Selling Products</p>
                <ul className="space-y-1.5 text-[11px]">
                  {previewProducts.map((p) => (
                    <li key={p.name} className="flex items-center justify-between text-foreground"><span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-accent" aria-hidden />{p.name}</span><span className="tabular text-muted">{p.units.toLocaleString()}</span></li>
                  ))}
                </ul>
              </div>
              <div className="rounded-md border border-border p-3">
                <p className="mb-1 text-xs font-semibold text-emphasis">Key Insights</p>
                <p className="text-[11px] leading-snug text-muted">Revenue increased by 12.3% compared to the previous period.</p>
              </div>
            </div>
          </div>

          {full && (
            <div className="mt-3 grid gap-3 lg:grid-cols-5">
              <div className="rounded-md border border-border p-3 lg:col-span-2">
                <p className="mb-1 text-xs font-semibold text-emphasis">Category Breakdown</p>
                <DonutChart data={previewCategories} height={110} legendValue="share" />
              </div>
              <div className="rounded-md border border-border p-3 lg:col-span-3">
                <p className="mb-1 text-xs font-semibold text-emphasis">Regional Performance</p>
                <BarChart data={previewRegions} xKey="name" series={[{ key: "value", label: "Revenue" }]} height={140} valueFormatter={(v) => f.currency(v, { compact: true })} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
