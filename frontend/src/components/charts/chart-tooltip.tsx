interface TooltipEntry {
  name?: string | number;
  value?: number | string | readonly (number | string)[];
  color?: string;
  dataKey?: string | number;
  payload?: Record<string, unknown>;
}

export interface ChartTooltipProps {
  active?: boolean;
  payload?: readonly TooltipEntry[];
  label?: string | number;
  valueFormatter?: (value: number) => string;
  labelFormatter?: (label: string) => string;
}

/** Theme-aware tooltip shared by every chart. Passed to recharts via `content={<ChartTooltip />}`. */
export function ChartTooltip({ active, payload, label, valueFormatter, labelFormatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const heading = label !== undefined && label !== "" ? (labelFormatter ? labelFormatter(String(label)) : String(label)) : undefined;
  return (
    <div className="min-w-40 rounded-lg border border-border bg-surface px-3 py-2 text-sm shadow-popover">
      {heading && <p className="mb-1.5 font-semibold text-emphasis">{heading}</p>}
      <ul className="space-y-1">
        {payload.map((entry, i) => {
          const value = typeof entry.value === "number" ? entry.value : Number(entry.value);
          return (
            <li key={`${entry.dataKey ?? entry.name}-${i}`} className="flex items-center justify-between gap-4">
              <span className="flex items-center gap-2 text-muted">
                <span className="size-2.5 rounded-sm" style={{ background: entry.color }} aria-hidden />
                {entry.name}
              </span>
              <span className="tabular font-medium text-foreground">
                {Number.isFinite(value) ? (valueFormatter ? valueFormatter(value) : value.toLocaleString()) : "—"}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
