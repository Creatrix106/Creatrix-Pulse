"use client";

import { useMemo, useState } from "react";
import { AreaChart, BarChart, ChartCard, LineChart, StackedBarChart } from "@/components/charts";
import { GroupBySelector, MetricSelector } from "@/components/filters/option-selectors";
import { EmptyState } from "@/components/feedback/empty-state";
import { QueryBoundary } from "@/components/feedback/query-boundary";
import { KpiGrid } from "@/components/dashboard/kpi-card";
import { METRIC_OPTIONS } from "@/config/filters";
import { useSalesQuery } from "@/hooks/use-analytics";
import { useAnalyticsFilters } from "@/hooks/use-analytics-filters";
import { useChartFormatters } from "@/hooks/use-chart-formatters";
import { useFiltersStore } from "@/stores/filters.store";
import type { SalesData } from "@/types/analytics";
import type { MetricKey } from "@/types/filters";
import { paletteColor } from "@/config/charts";

const SALES_METRICS: MetricKey[] = ["revenue", "orders", "units", "aov"];

function SalesContent({ data }: { data: SalesData }) {
  const { groupBy, comparison } = useAnalyticsFilters();
  const setGroupBy = useFiltersStore((s) => s.setGroupBy);
  const fmt = useChartFormatters(groupBy);
  const [metric, setMetric] = useState<MetricKey>("revenue");
  const option = METRIC_OPTIONS.find((m) => m.value === metric) ?? METRIC_OPTIONS[0];
  const valueFmt = option.format === "currency" ? fmt.currency : fmt.number;
  const axisFmt = option.format === "currency" ? fmt.currencyAxis : fmt.numberAxis;

  // Previous-period values are aligned to the current period by position.
  const trendData = useMemo(
    () =>
      data.trend.map((p, i) => ({
        date: p.date,
        current: p[metric] ?? 0,
        previous: data.previousTrend?.[i]?.[metric],
      })),
    [data, metric],
  );

  const stackedData = useMemo(() => data.categoryTrend.map((p) => ({ date: p.date, ...p.values })), [data.categoryTrend]);

  if (data.trend.length === 0) {
    return <EmptyState title="No sales in this period" description="Try widening the date range or clearing category and region filters." />;
  }

  return (
    <div className="space-y-6">
      <KpiGrid kpis={data.kpis} />

      <ChartCard
        title={`${option.label} trend`}
        description={comparison === "none" ? "Choose “Previous period” in the filter bar to compare date ranges." : "Current period compared with the previous period"}
        actions={
          <>
            <MetricSelector value={metric} onChange={setMetric} metrics={SALES_METRICS} className="w-48" />
            <GroupBySelector value={groupBy} onChange={setGroupBy} className="w-32" />
          </>
        }
      >
        <LineChart
          data={trendData}
          xKey="date"
          series={[
            { key: "current", label: "Current period", color: "var(--chart-1)" },
            ...(data.previousTrend ? [{ key: "previous", label: "Previous period", color: "var(--chart-6)", dashed: true }] : []),
          ]}
          valueFormatter={valueFmt}
          axisFormatter={axisFmt}
          xFormatter={fmt.xFormatter}
          tooltipLabelFormatter={fmt.tooltipLabel}
          height={320}
          ariaLabel={`${option.label} trend`}
        />
      </ChartCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Order trend" description="Orders per period">
          <BarChart data={data.trend} xKey="date" series={[{ key: "orders", label: "Orders" }]} valueFormatter={fmt.number} axisFormatter={fmt.numberAxis} xFormatter={fmt.xFormatter} tooltipLabelFormatter={fmt.tooltipLabel} height={260} />
        </ChartCard>
        <ChartCard title="Units sold" description="Units per period">
          <AreaChart data={data.trend} xKey="date" series={[{ key: "units", label: "Units sold", color: "var(--chart-4)" }]} valueFormatter={fmt.number} axisFormatter={fmt.numberAxis} xFormatter={fmt.xFormatter} tooltipLabelFormatter={fmt.tooltipLabel} height={260} />
        </ChartCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Average order value" description="Revenue per order">
          <LineChart data={data.trend} xKey="date" series={[{ key: "aov", label: "Avg. order value", color: "var(--chart-5)" }]} valueFormatter={fmt.currency} axisFormatter={fmt.currencyAxis} xFormatter={fmt.xFormatter} tooltipLabelFormatter={fmt.tooltipLabel} height={260} />
        </ChartCard>
        <ChartCard title="Sales by category over time" description="Revenue split by category">
          <StackedBarChart
            data={stackedData}
            xKey="date"
            series={data.categoryNames.map((name, i) => ({ key: name, label: name, color: paletteColor(i) }))}
            valueFormatter={fmt.currency}
            axisFormatter={fmt.currencyAxis}
            xFormatter={fmt.xFormatter}
            tooltipLabelFormatter={fmt.tooltipLabel}
            height={260}
          />
        </ChartCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Sales by category" description="Total revenue">
          <BarChart orientation="vertical" data={data.categories} xKey="name" series={[{ key: "value", label: "Revenue" }]} valueFormatter={fmt.currency} axisFormatter={fmt.currencyAxis} height={260} />
        </ChartCard>
        <ChartCard title="Sales by region" description="Total revenue">
          <BarChart orientation="vertical" data={data.regions} xKey="name" series={[{ key: "value", label: "Revenue", color: "var(--chart-4)" }]} valueFormatter={fmt.currency} axisFormatter={fmt.currencyAxis} height={260} emptyMessage="This dataset has no region column." />
        </ChartCard>
      </div>
    </div>
  );
}

export function SalesView() {
  const query = useSalesQuery();
  return <QueryBoundary query={query}>{(data) => <SalesContent data={data} />}</QueryBoundary>;
}
