"use client";

import { chartConfig } from "@/config/charts";
import { BarChart } from "./bar-chart";

interface HistogramProps {
  bins: { label: string; count: number }[];
  seriesLabel?: string;
  height?: number;
  emptyMessage?: string;
  valueFormatter?: (value: number) => string;
}

/** Distribution chart: contiguous bars over pre-binned data (binning is done by the backend). */
export function Histogram({ bins, seriesLabel = "Count", height = chartConfig.height, emptyMessage, valueFormatter }: HistogramProps) {
  return (
    <BarChart
      data={bins}
      xKey="label"
      series={[{ key: "count", label: seriesLabel }]}
      gap={0.04}
      height={height}
      emptyMessage={emptyMessage}
      valueFormatter={valueFormatter}
      ariaLabel="Histogram"
    />
  );
}
