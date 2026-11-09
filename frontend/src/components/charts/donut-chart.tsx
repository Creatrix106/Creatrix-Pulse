"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { chartConfig, paletteColor } from "@/config/charts";
import { ChartLegend } from "./chart-legend";
import { ChartTooltip } from "./chart-tooltip";
import { EmptyChartState } from "./empty-chart-state";

export interface DonutDatum {
  name: string;
  value: number;
  share?: number;
}

interface DonutChartProps {
  data: DonutDatum[];
  valueFormatter?: (value: number) => string;
  centerLabel?: string;
  centerValue?: string;
  height?: number;
  emptyMessage?: string;
  legendValue?: "share" | "value";
}

export function DonutChart({ data, valueFormatter, centerLabel, centerValue, height = 200, emptyMessage, legendValue = "share" }: DonutChartProps) {
  if (data.length === 0 || data.every((d) => d.value === 0)) return <EmptyChartState message={emptyMessage} height={height} />;
  const total = data.reduce((s, d) => s + d.value, 0);
  const share = (d: DonutDatum) => d.share ?? (total ? (d.value / total) * 100 : 0);

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row" role="img" aria-label="Donut chart">
      <div className="relative w-full max-w-[220px] shrink-0" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="64%" outerRadius="100%" paddingAngle={2} stroke="var(--surface)" strokeWidth={2} animationDuration={chartConfig.animationDuration}>
              {data.map((d, i) => (
                <Cell key={d.name} fill={paletteColor(i)} />
              ))}
            </Pie>
            <Tooltip content={<ChartTooltip valueFormatter={valueFormatter} />} />
          </PieChart>
        </ResponsiveContainer>
        {(centerLabel || centerValue) && (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
            {centerValue && <span className="tabular text-lg font-semibold text-emphasis">{centerValue}</span>}
            {centerLabel && <span className="text-xs text-muted">{centerLabel}</span>}
          </div>
        )}
      </div>
      <ChartLegend
        stacked
        className="w-full"
        items={data.map((d, i) => ({
          label: d.name,
          color: paletteColor(i),
          value: legendValue === "share" ? `${share(d).toFixed(1)}%` : valueFormatter?.(d.value) ?? String(d.value),
        }))}
      />
    </div>
  );
}
