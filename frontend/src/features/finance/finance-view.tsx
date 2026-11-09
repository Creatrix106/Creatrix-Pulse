"use client";

import { AreaChart, BarChart, ChartCard, LineChart } from "@/components/charts";
import { CapabilityGate } from "@/components/dashboard/capability-gate";
import { KpiGrid } from "@/components/dashboard/kpi-card";
import { QueryBoundary } from "@/components/feedback/query-boundary";
import { chartConfig } from "@/config/charts";
import { useFinanceQuery } from "@/hooks/use-analytics";
import { useAnalyticsFilters } from "@/hooks/use-analytics-filters";
import { useChartFormatters } from "@/hooks/use-chart-formatters";
import type { FinanceData } from "@/types/analytics";

function FinanceContent({ data }: { data: FinanceData }) {
  const { groupBy } = useAnalyticsFilters();
  const fmt = useChartFormatters(groupBy);
  const axis = { xFormatter: fmt.xFormatter, tooltipLabelFormatter: fmt.tooltipLabel };

  return (
    <div className="space-y-6">
      <KpiGrid kpis={data.kpis} />

      <ChartCard title="Revenue vs. cost" description="Revenue, cost and gross profit over time">
        <AreaChart
          data={data.trend}
          xKey="date"
          series={[
            { key: "revenue", label: "Revenue", color: chartConfig.semantic.current },
            { key: "cost", label: "Cost", color: chartConfig.semantic.cost },
            { key: "profit", label: "Gross profit", color: chartConfig.semantic.profit },
          ]}
          valueFormatter={fmt.currency}
          axisFormatter={fmt.currencyAxis}
          height={320}
          {...axis}
        />
      </ChartCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Profit margin trend" description="Gross profit as a percentage of revenue">
          <LineChart data={data.trend} xKey="date" series={[{ key: "margin", label: "Margin", color: chartConfig.semantic.profit }]} valueFormatter={fmt.percent} axisFormatter={fmt.percentAxis} height={280} {...axis} />
        </ChartCard>
        <ChartCard title="Margin by category" description="Gross margin per category">
          <BarChart orientation="vertical" data={data.categoryMargins} xKey="name" series={[{ key: "value", label: "Margin", color: chartConfig.semantic.profit }]} valueFormatter={fmt.percent} axisFormatter={fmt.percentAxis} height={280} categoryWidth={120} />
        </ChartCard>
      </div>

      <ChartCard title="Gross profit" description="Profit per period">
        <BarChart data={data.trend} xKey="date" series={[{ key: "profit", label: "Gross profit", color: chartConfig.semantic.profit }]} valueFormatter={fmt.currency} axisFormatter={fmt.currencyAxis} height={260} {...axis} />
      </ChartCard>
    </div>
  );
}

export function FinanceView() {
  const query = useFinanceQuery();
  return (
    <QueryBoundary query={query}>
      {(result) => (
        <CapabilityGate result={result} title="Financial analytics are unavailable for this dataset">
          {(data) => <FinanceContent data={data} />}
        </CapabilityGate>
      )}
    </QueryBoundary>
  );
}
