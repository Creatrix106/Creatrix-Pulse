"use client";

import { useFormatters } from "@/hooks/use-formatters";
import type { ProductPerformance } from "@/types/analytics";
import { EmptyChartState } from "@/components/charts/empty-chart-state";
import { TrendIndicator } from "./trend-indicator";

interface TopProductsListProps {
  products: ProductPerformance[];
  emptyMessage?: string;
  /** Show the rank as a medal-less index. */
  showChange?: boolean;
}

export function TopProductsList({ products, emptyMessage, showChange = true }: TopProductsListProps) {
  const f = useFormatters();
  if (products.length === 0) return <EmptyChartState message={emptyMessage ?? "No product data for this selection."} height={200} />;
  const max = Math.max(...products.map((p) => p.revenue), 1);

  return (
    <ol className="space-y-3">
      {products.map((p, i) => (
        <li key={p.id} className="flex items-center gap-3">
          <span className="grid size-6 shrink-0 place-items-center rounded-full bg-accent-soft text-xs font-semibold text-accent">{i + 1}</span>
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-3">
              <p className="truncate text-sm font-medium text-foreground">{p.name}</p>
              <p className="tabular shrink-0 text-sm font-semibold text-emphasis">{f.currency(p.revenue, { compact: true })}</p>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-accent" aria-hidden>
              <div className="h-full rounded-full bg-accent" style={{ width: `${(p.revenue / max) * 100}%` }} />
            </div>
            <div className="mt-1 flex justify-between text-xs text-muted">
              <span>{f.number(p.units)} units · {p.category}</span>
              {showChange && p.change !== null && p.change !== undefined && <TrendIndicator value={p.change} className="text-xs" />}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
