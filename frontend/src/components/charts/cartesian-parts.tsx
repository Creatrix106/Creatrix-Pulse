import type { ReactElement } from "react";
import { CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import { chartConfig, paletteColor } from "@/config/charts";
import { ChartTooltip } from "./chart-tooltip";
import type { ChartSeries } from "./types";

interface PartsOptions {
  xKey: string;
  xFormatter?: (value: string) => string;
  axisFormatter?: (value: number) => string;
  valueFormatter?: (value: number) => string;
  tooltipLabelFormatter?: (value: string) => string;
  yWidth?: number;
}

/** Grid, axes and tooltip shared by line / area / bar charts. */
export function cartesianParts(o: PartsOptions): ReactElement[] {
  return [
    <CartesianGrid key="grid" vertical={false} {...chartConfig.grid} />,
    <XAxis
      key="x"
      dataKey={o.xKey}
      tick={chartConfig.tick}
      tickLine={false}
      axisLine={chartConfig.axisLine}
      tickFormatter={o.xFormatter}
      tickMargin={8}
      minTickGap={16}
    />,
    <YAxis
      key="y"
      tick={chartConfig.tick}
      tickLine={false}
      axisLine={false}
      width={o.yWidth ?? 56}
      tickFormatter={o.axisFormatter ?? o.valueFormatter}
    />,
    <Tooltip
      key="tip"
      cursor={{ stroke: "var(--border-strong)", fill: "var(--surface-accent)", fillOpacity: 0.5 }}
      content={<ChartTooltip valueFormatter={o.valueFormatter} labelFormatter={o.tooltipLabelFormatter} />}
    />,
  ];
}

export function seriesColor(series: ChartSeries, index: number): string {
  return series.color ?? paletteColor(index);
}
