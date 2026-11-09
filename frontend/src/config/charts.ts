/** Shared chart configuration. Colors reference CSS variables so charts follow the active theme. */
export const chartPalette = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
] as const;

export const chartConfig = {
  height: 300,
  compactHeight: 220,
  margin: { top: 8, right: 12, bottom: 0, left: 0 },
  grid: { stroke: "var(--chart-grid)", strokeDasharray: "3 3" },
  tick: { fontSize: 12, fill: "var(--muted)" },
  axisLine: { stroke: "var(--border)" },
  animationDuration: 600,
  /** Colors with semantic meaning. */
  semantic: {
    current: "var(--chart-1)",
    previous: "var(--chart-6)",
    cost: "var(--chart-5)",
    profit: "var(--chart-4)",
  },
} as const;

export function paletteColor(index: number): string {
  return chartPalette[index % chartPalette.length];
}
