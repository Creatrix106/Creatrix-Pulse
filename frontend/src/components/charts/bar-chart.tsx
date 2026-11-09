"use client";

import { Bar, BarChart as RBarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { chartConfig } from "@/config/charts";
import { cartesianParts, seriesColor } from "./cartesian-parts";
import { ChartLegend } from "./chart-legend";
import { ChartTooltip } from "./chart-tooltip";
import { EmptyChartState } from "./empty-chart-state";
import type { CartesianChartProps } from "./types";

export interface BarChartProps<T extends object> extends CartesianChartProps<T> {
  /** "horizontal" = vertical columns (default). "vertical" = horizontal bars, good for long labels. */
  orientation?: "horizontal" | "vertical";
  stacked?: boolean;
  /** Fraction (0-1) of gap between bars. */
  gap?: number;
  categoryWidth?: number;
}

export function BarChart<T extends object>({
  data,
  xKey,
  series,
  height = chartConfig.height,
  showLegend = series.length > 1,
  emptyMessage,
  ariaLabel,
  orientation = "horizontal",
  stacked = false,
  gap = 0.25,
  categoryWidth = 110,
  ...format
}: BarChartProps<T>) {
  if (data.length === 0) return <EmptyChartState message={emptyMessage} height={height} />;
  const horizontalBars = orientation === "vertical";
  const radius: [number, number, number, number] = horizontalBars ? [0, 4, 4, 0] : [4, 4, 0, 0];

  return (
    <div role="img" aria-label={ariaLabel ?? "Bar chart"}>
      <ResponsiveContainer width="100%" height={height} minWidth={0}>
        <RBarChart
          data={data as T[]}
          layout={horizontalBars ? "vertical" : "horizontal"}
          margin={chartConfig.margin}
          barCategoryGap={`${Math.round(gap * 100)}%`}
        >
          {horizontalBars ? (
            [
              <CartesianGrid key="grid" horizontal={false} {...chartConfig.grid} />,
              <XAxis key="x" type="number" tick={chartConfig.tick} tickLine={false} axisLine={false} tickFormatter={format.axisFormatter ?? format.valueFormatter} />,
              <YAxis key="y" type="category" dataKey={xKey as string} width={categoryWidth} tick={chartConfig.tick} tickLine={false} axisLine={chartConfig.axisLine} tickFormatter={format.xFormatter} />,
              <Tooltip key="tip" cursor={{ fill: "var(--surface-accent)", fillOpacity: 0.5 }} content={<ChartTooltip valueFormatter={format.valueFormatter} labelFormatter={format.tooltipLabelFormatter} />} />,
            ]
          ) : (
            cartesianParts({ xKey, ...format })
          )}
          {series.map((s, i) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.label}
              fill={seriesColor(s, i)}
              stackId={stacked ? "stack" : undefined}
              radius={stacked ? 0 : radius}
              maxBarSize={44}
              animationDuration={chartConfig.animationDuration}
            />
          ))}
        </RBarChart>
      </ResponsiveContainer>
      {showLegend && <ChartLegend className="mt-3" items={series.map((s, i) => ({ label: s.label, color: seriesColor(s, i) }))} />}
    </div>
  );
}
