"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { AreaChart, BarChart, ChartCard, DonutChart } from "@/components/charts";
import { EmptyState } from "@/components/feedback/empty-state";
import { QueryBoundary } from "@/components/feedback/query-boundary";
import { InsightCard } from "@/components/dashboard/insight-card";
import { KpiGrid } from "@/components/dashboard/kpi-card";
import { TopProductsList } from "@/components/dashboard/top-products-list";
import { getDashboardHref } from "@/config/navigation";
import { useOverviewQuery } from "@/hooks/use-analytics";
import { useAnalyticsFilters } from "@/hooks/use-analytics-filters";
import { useChartFormatters } from "@/hooks/use-chart-formatters";
import { useDatasetId } from "@/hooks/use-dataset-id";
import { usePreferencesStore } from "@/stores/preferences.store";
import type { OverviewData } from "@/types/analytics";

function OverviewContent({ data }: { data: OverviewData }) {
  const datasetId = useDatasetId();
  const { groupBy } = useAnalyticsFilters();
  const fmt = useChartFormatters(groupBy);
  const showInsights = usePreferencesStore((s) => s.showInsightsOnOverview);
  const totalRevenue = data.categories.reduce((s, c) => s + c.value, 0);

  if (data.revenueTrend.length === 0) {
    return <EmptyState title="No records match these filters" description="Try widening the date range or clearing category and region filters." />;
  }

  return (
    <div className="space-y-6">
      <KpiGrid kpis={data.kpis} />

      <div className="grid gap-6 lg:grid-cols-3">
        <ChartCard title="Revenue trend" description="Revenue over the selected period" className="lg:col-span-2">
          <AreaChart
            data={data.revenueTrend}
            xKey="date"
            series={[{ key: "revenue", label: "Revenue" }]}
            valueFormatter={fmt.currency}
            axisFormatter={fmt.currencyAxis}
            xFormatter={fmt.xFormatter}
            tooltipLabelFormatter={fmt.tooltipLabel}
            ariaLabel="Revenue trend"
          />
        </ChartCard>
        <ChartCard title="Top-selling products" description="Ranked by revenue">
          <TopProductsList products={data.topProducts} />
        </ChartCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <ChartCard title="Category breakdown" description="Share of revenue">
          <DonutChart data={data.categories} valueFormatter={fmt.currency} centerValue={fmt.currencyAxis(totalRevenue)} centerLabel="Total revenue" />
        </ChartCard>
        <ChartCard title="Regional performance" description="Revenue by region">
          <BarChart
            data={data.regions}
            xKey="name"
            series={[{ key: "value", label: "Revenue" }]}
            valueFormatter={fmt.currency}
            axisFormatter={fmt.currencyAxis}
            height={240}
            emptyMessage="This dataset has no region column."
            ariaLabel="Revenue by region"
          />
        </ChartCard>
        {showInsights && (
          <ChartCard
            title="Key insights"
            description="Generated from your data"
            footer={
              <Link href={getDashboardHref(datasetId, "insights")} className="inline-flex items-center gap-1 font-medium text-accent hover:underline">
                View all insights <ArrowRight className="size-4" aria-hidden />
              </Link>
            }
          >
            {data.insights.length === 0 ? (
              <p className="text-sm text-muted">No insights available for this selection.</p>
            ) : (
              <div className="space-y-3">
                {data.insights.slice(0, 3).map((insight) => (
                  <InsightCard key={insight.id} insight={insight} compact />
                ))}
              </div>
            )}
          </ChartCard>
        )}
      </div>
    </div>
  );
}

export function OverviewView() {
  const query = useOverviewQuery();
  return <QueryBoundary query={query}>{(data) => <OverviewContent data={data} />}</QueryBoundary>;
}
