export interface ChartSeries {
  key: string;
  label: string;
  /** CSS color or var(--token). Defaults to the shared palette by index. */
  color?: string;
  dashed?: boolean;
}

export interface CartesianChartProps<T extends object> {
  data: readonly T[];
  xKey: keyof T & string;
  series: ChartSeries[];
  height?: number;
  valueFormatter?: (value: number) => string;
  /** Axis tick formatter. Falls back to valueFormatter. */
  axisFormatter?: (value: number) => string;
  xFormatter?: (value: string) => string;
  /** Longer label shown in the tooltip header. */
  tooltipLabelFormatter?: (value: string) => string;
  showLegend?: boolean;
  emptyMessage?: string;
  ariaLabel?: string;
}
