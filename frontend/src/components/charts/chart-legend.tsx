import { cn } from "@/utils/cn";

export interface LegendItem {
  label: string;
  color: string;
  /** Optional trailing value (e.g. "38.3%"). */
  value?: string;
  dashed?: boolean;
}

export function ChartLegend({ items, className, stacked }: { items: LegendItem[]; className?: string; stacked?: boolean }) {
  if (items.length === 0) return null;
  return (
    <ul className={cn(stacked ? "space-y-2" : "flex flex-wrap gap-x-5 gap-y-1.5", "text-sm", className)} aria-label="Chart legend">
      {items.map((item) => (
        <li key={item.label} className={cn("flex items-center gap-2 text-muted", stacked && "justify-between")}>
          <span className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              style={item.dashed ? { border: `2px dashed ${item.color}` } : { background: item.color }}
              aria-hidden
            />
            {item.label}
          </span>
          {item.value && <span className="tabular font-medium text-foreground">{item.value}</span>}
        </li>
      ))}
    </ul>
  );
}
