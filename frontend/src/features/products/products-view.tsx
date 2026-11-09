"use client";

import { useMemo } from "react";
import { BarChart, ChartCard, DonutChart, ScatterChart } from "@/components/charts";
import { EmptyState } from "@/components/feedback/empty-state";
import { QueryBoundary } from "@/components/feedback/query-boundary";
import { TopProductsList } from "@/components/dashboard/top-products-list";
import { TrendIndicator } from "@/components/dashboard/trend-indicator";
import { DataTable } from "@/components/tables/data-table";
import { useProductsQuery } from "@/hooks/use-analytics";
import { useChartFormatters } from "@/hooks/use-chart-formatters";
import { useFormatters } from "@/hooks/use-formatters";
import type { ProductPerformance, ProductsData } from "@/types/analytics";
import type { TableColumn } from "@/types/table";
import { contributionSlices } from "./utils";

function ProductsContent({ data }: { data: ProductsData }) {
  const f = useFormatters();
  const fmt = useChartFormatters();
  const hasMargin = data.all.some((p) => p.margin !== null && p.margin !== undefined);

  const columns = useMemo<TableColumn<ProductPerformance>[]>(
    () => [
      { key: "rank", header: "#", accessor: (p) => data.all.indexOf(p) + 1, type: "number", filterable: false },
      { key: "name", header: "Product", accessor: (p) => p.name },
      { key: "category", header: "Category", accessor: (p) => p.category },
      { key: "revenue", header: "Revenue", accessor: (p) => p.revenue, type: "number", render: (p) => f.currency(p.revenue) },
      { key: "units", header: "Units", accessor: (p) => p.units, type: "number", render: (p) => f.number(p.units) },
      { key: "orders", header: "Orders", accessor: (p) => p.orders, type: "number", render: (p) => f.number(p.orders) },
      { key: "share", header: "Revenue share", accessor: (p) => Number(p.share.toFixed(1)), type: "number", render: (p) => f.percent(p.share) },
      {
        key: "change",
        header: "Change",
        accessor: (p) => (p.change === null || p.change === undefined ? null : Number(p.change.toFixed(1))),
        type: "number",
        render: (p) => (p.change === null || p.change === undefined ? <span className="text-muted">—</span> : <TrendIndicator value={p.change} className="justify-end" />),
      },
      ...(hasMargin
        ? [{ key: "margin", header: "Margin", accessor: (p: ProductPerformance) => (p.margin == null ? null : Number(p.margin.toFixed(1))), type: "number" as const, render: (p: ProductPerformance) => (p.margin == null ? "—" : f.percent(p.margin)) }]
        : []),
    ],
    [data.all, f, hasMargin],
  );

  if (data.all.length === 0) {
    return <EmptyState title="No products in this selection" description="Try widening the date range or clearing filters." />;
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Top-selling products" description="Highest revenue in the period">
          <TopProductsList products={data.top} />
        </ChartCard>
        <ChartCard title="Low-performing products" description="Lowest revenue in the period">
          <TopProductsList products={data.low} />
        </ChartCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Category performance" description="Revenue by category">
          <BarChart orientation="vertical" data={data.categories} xKey="name" series={[{ key: "value", label: "Revenue" }]} valueFormatter={fmt.currency} axisFormatter={fmt.currencyAxis} height={280} categoryWidth={120} />
        </ChartCard>
        <ChartCard title="Revenue contribution" description="Top products vs. the rest">
          <DonutChart data={contributionSlices(data.all)} valueFormatter={fmt.currency} height={220} />
        </ChartCard>
      </div>

      <ChartCard title="Product comparison" description="Units sold against revenue – products above the trend earn more per unit">
        <ScatterChart
          data={data.all.map((p) => ({ name: p.name, x: p.units, y: p.revenue }))}
          xLabel="Units sold"
          yLabel="Revenue"
          xFormatter={fmt.numberAxis}
          yFormatter={fmt.currencyAxis}
          height={320}
        />
      </ChartCard>

      <ChartCard title="Product rankings" description="Sort, filter and export every product">
        <DataTable data={data.all} columns={columns} getRowId={(p) => p.id} caption="Product rankings" pageSize={10} initialSort={{ key: "revenue", direction: "desc" }} />
      </ChartCard>
    </div>
  );
}

export function ProductsView() {
  const query = useProductsQuery();
  return <QueryBoundary query={query}>{(data) => <ProductsContent data={data} />}</QueryBoundary>;
}
