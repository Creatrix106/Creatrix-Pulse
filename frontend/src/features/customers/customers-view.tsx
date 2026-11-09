"use client";

import { useMemo } from "react";
import { ChartCard, DonutChart, Histogram, StackedBarChart } from "@/components/charts";
import { CapabilityGate } from "@/components/dashboard/capability-gate";
import { KpiGrid } from "@/components/dashboard/kpi-card";
import { QueryBoundary } from "@/components/feedback/query-boundary";
import { Card } from "@/components/ui/card";
import { useCustomersQuery } from "@/hooks/use-analytics";
import { useAnalyticsFilters } from "@/hooks/use-analytics-filters";
import { useChartFormatters } from "@/hooks/use-chart-formatters";
import { useFormatters } from "@/hooks/use-formatters";
import type { CustomersData } from "@/types/analytics";

function CustomersContent({ data }: { data: CustomersData }) {
  const { groupBy } = useAnalyticsFilters();
  const fmt = useChartFormatters(groupBy);
  const f = useFormatters();
  const total = data.distribution.reduce((s, d) => s + d.value, 0);
  const stackSeries = useMemo(
    () => [
      { key: "newCustomers", label: "New customers", color: "var(--chart-1)" },
      { key: "returningCustomers", label: "Returning customers", color: "var(--chart-4)" },
    ],
    [],
  );

  return (
    <div className="space-y-6">
      <KpiGrid kpis={data.kpis} />

      <div className="grid gap-6 lg:grid-cols-3">
        <ChartCard title="New vs. returning customers" description="Customers ordering in each period" className="lg:col-span-2">
          <StackedBarChart data={data.newVsReturning} xKey="date" series={stackSeries} valueFormatter={fmt.number} axisFormatter={fmt.numberAxis} xFormatter={fmt.xFormatter} tooltipLabelFormatter={fmt.tooltipLabel} />
        </ChartCard>
        <ChartCard title="Customer distribution" description="Distinct customers by region">
          <DonutChart data={data.distribution} valueFormatter={fmt.number} centerValue={f.number(total)} centerLabel="Customer-region pairs" />
        </ChartCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Purchase frequency" description="Customers by number of orders in the period">
          <Histogram bins={data.frequency} seriesLabel="Customers" valueFormatter={fmt.number} height={280} />
        </ChartCard>
        <ChartCard title="Customer segments" description="Grouped by purchase frequency">
          <ul className="space-y-3">
            {data.segments.map((s) => (
              <li key={s.name}>
                <Card className="bg-surface-muted p-4 shadow-none">
                  <div className="flex items-baseline justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-emphasis">{s.name}</p>
                      <p className="text-xs text-muted">{s.description}</p>
                    </div>
                    <p className="tabular text-sm font-semibold text-emphasis">{f.number(s.customers)} customers</p>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-accent" aria-hidden>
                    <div className="h-full rounded-full bg-accent" style={{ width: `${s.share}%` }} />
                  </div>
                  <p className="mt-1.5 flex justify-between text-xs text-muted">
                    <span>{f.percent(s.share)} of customers</span>
                    <span>{f.currency(s.revenue, { compact: true })} revenue</span>
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        </ChartCard>
      </div>
    </div>
  );
}

export function CustomersView() {
  const query = useCustomersQuery();
  return (
    <QueryBoundary query={query}>
      {(result) => (
        <CapabilityGate result={result} title="Customer analytics are unavailable for this dataset">
          {(data) => <CustomersContent data={data} />}
        </CapabilityGate>
      )}
    </QueryBoundary>
  );
}
