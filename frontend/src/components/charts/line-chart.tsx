"use client";

import { Line, LineChart as RLineChart, ResponsiveContainer } from "recharts";
import { chartConfig } from "@/config/charts";
import { cartesianParts, seriesColor } from "./cartesian-parts";
import { ChartLegend } from "./chart-legend";
import { EmptyChartState } from "./empty-chart-state";
import type { CartesianChartProps } from "./types";

export function LineChart<T extends object>({
  data,
  xKey,
  series,
  height = chartConfig.height,
  showLegend = series.length > 1,
  emptyMessage,
  ariaLabel,
  ...format
}: CartesianChartProps<T>) {
  if (data.length === 0) return <EmptyChartState message={emptyMessage} height={height} />;
  return (
    <div role="img" aria-label={ariaLabel ?? "Line chart"}>
      <ResponsiveContainer width="100%" height={height} minWidth={0}>
        <RLineChart data={data as T[]} margin={chartConfig.margin}>
          {cartesianParts({ xKey, ...format })}
          {series.map((s, i) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={seriesColor(s, i)}
              strokeWidth={2.25}
              strokeDasharray={s.dashed ? "5 4" : undefined}
              dot={data.length <= 24 && !s.dashed ? { r: 3, strokeWidth: 0, fill: seriesColor(s, i) } : false}
              activeDot={{ r: 5 }}
              connectNulls
              animationDuration={chartConfig.animationDuration}
            />
          ))}
        </RLineChart>
      </ResponsiveContainer>
      {showLegend && <ChartLegend className="mt-3" items={series.map((s, i) => ({ label: s.label, color: seriesColor(s, i), dashed: s.dashed }))} />}
    </div>
  );
}
