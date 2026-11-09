"use client";

import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart as RScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { chartConfig } from "@/config/charts";
import { EmptyChartState } from "./empty-chart-state";

export interface ScatterDatum {
  name: string;
  x: number;
  y: number;
  size?: number;
}

interface ScatterChartProps {
  data: ScatterDatum[];
  xLabel: string;
  yLabel: string;
  xFormatter?: (value: number) => string;
  yFormatter?: (value: number) => string;
  height?: number;
  emptyMessage?: string;
}

interface PointTooltipProps {
  active?: boolean;
  payload?: readonly { payload?: ScatterDatum }[];
  xLabel: string;
  yLabel: string;
  xFormatter: (v: number) => string;
  yFormatter: (v: number) => string;
}

function PointTooltip({ active, payload, xLabel, yLabel, xFormatter, yFormatter }: PointTooltipProps) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-sm shadow-popover">
      <p className="mb-1 font-semibold text-emphasis">{point.name}</p>
      <p className="text-muted">{xLabel}: <span className="font-medium text-foreground">{xFormatter(point.x)}</span></p>
      <p className="text-muted">{yLabel}: <span className="font-medium text-foreground">{yFormatter(point.y)}</span></p>
    </div>
  );
}

export function ScatterChart({ data, xLabel, yLabel, xFormatter = String, yFormatter = String, height = chartConfig.height, emptyMessage }: ScatterChartProps) {
  if (data.length === 0) return <EmptyChartState message={emptyMessage} height={height} />;
  return (
    <div role="img" aria-label={`Scatter chart of ${yLabel} against ${xLabel}`}>
      <ResponsiveContainer width="100%" height={height} minWidth={0}>
        <RScatterChart margin={{ top: 8, right: 16, bottom: 20, left: 0 }}>
          <CartesianGrid {...chartConfig.grid} />
          <XAxis type="number" dataKey="x" name={xLabel} tick={chartConfig.tick} tickLine={false} axisLine={chartConfig.axisLine} tickFormatter={xFormatter} label={{ value: xLabel, position: "bottom", offset: 4, fill: "var(--muted)", fontSize: 12 }} />
          <YAxis type="number" dataKey="y" name={yLabel} width={64} tick={chartConfig.tick} tickLine={false} axisLine={false} tickFormatter={yFormatter} />
          <ZAxis type="number" dataKey="size" range={[70, 70]} />
          <Tooltip cursor={{ strokeDasharray: "3 3", stroke: "var(--border-strong)" }} content={<PointTooltip xLabel={xLabel} yLabel={yLabel} xFormatter={xFormatter} yFormatter={yFormatter} />} />
          <Scatter data={data} fill="var(--chart-1)" fillOpacity={0.85} animationDuration={chartConfig.animationDuration} />
        </RScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
