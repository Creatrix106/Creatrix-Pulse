"use client";

import { useId } from "react";
import { Area, AreaChart as RAreaChart, ResponsiveContainer } from "recharts";
import { chartConfig } from "@/config/charts";
import { cartesianParts, seriesColor } from "./cartesian-parts";
import { ChartLegend } from "./chart-legend";
import { EmptyChartState } from "./empty-chart-state";
import type { CartesianChartProps } from "./types";

export function AreaChart<T extends object>({
  data,
  xKey,
  series,
  height = chartConfig.height,
  showLegend = series.length > 1,
  emptyMessage,
  ariaLabel,
  ...format
}: CartesianChartProps<T>) {
  const uid = useId().replace(/:/g, "");
  if (data.length === 0) return <EmptyChartState message={emptyMessage} height={height} />;
  return (
    <div role="img" aria-label={ariaLabel ?? "Area chart"}>
      <ResponsiveContainer width="100%" height={height} minWidth={0}>
        <RAreaChart data={data as T[]} margin={chartConfig.margin}>
          <defs>
            {series.map((s, i) => (
              <linearGradient key={s.key} id={`${uid}-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={seriesColor(s, i)} stopOpacity={0.28} />
                <stop offset="100%" stopColor={seriesColor(s, i)} stopOpacity={0.02} />
              </linearGradient>
            ))}
          </defs>
          {cartesianParts({ xKey, ...format })}
          {series.map((s, i) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={seriesColor(s, i)}
              strokeWidth={2.25}
              strokeDasharray={s.dashed ? "5 4" : undefined}
              fill={s.dashed ? "transparent" : `url(#${uid}-${s.key})`}
              activeDot={{ r: 5 }}
              connectNulls
              animationDuration={chartConfig.animationDuration}
            />
          ))}
        </RAreaChart>
      </ResponsiveContainer>
      {showLegend && <ChartLegend className="mt-3" items={series.map((s, i) => ({ label: s.label, color: seriesColor(s, i), dashed: s.dashed }))} />}
    </div>
  );
}
