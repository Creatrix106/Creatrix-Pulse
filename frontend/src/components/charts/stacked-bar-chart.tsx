"use client";

import { BarChart, type BarChartProps } from "./bar-chart";

/** Bar chart with series stacked on top of each other. */
export function StackedBarChart<T extends object>(props: Omit<BarChartProps<T>, "stacked">) {
  return <BarChart {...props} stacked ariaLabel={props.ariaLabel ?? "Stacked bar chart"} />;
}
