import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { cn } from "@/utils/cn";

interface TrendIndicatorProps {
  /** Percent (or percentage-point) change. */
  value: number;
  /** True when a decrease is good (e.g. costs). */
  inverse?: boolean;
  suffix?: string;
  className?: string;
}

export function TrendIndicator({ value, inverse, suffix = "%", className }: TrendIndicatorProps) {
  const flat = Math.abs(value) < 0.05;
  const good = inverse ? value < 0 : value > 0;
  const Icon = flat ? Minus : value > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={cn("tabular inline-flex items-center gap-0.5 text-sm font-medium", flat ? "text-muted" : good ? "text-success" : "text-danger", className)}>
      <Icon className="size-4" aria-hidden />
      <span className="sr-only">{value >= 0 ? "Increase of" : "Decrease of"}</span>
      {Math.abs(value).toFixed(1)}
      {suffix}
    </span>
  );
}

interface ComparisonBadgeProps extends Omit<TrendIndicatorProps, "className"> {
  label?: string;
}

/** Trend value plus the comparison context ("vs previous period"). */
export function ComparisonBadge({ label = "vs previous period", ...trend }: ComparisonBadgeProps) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <TrendIndicator {...trend} />
      <span className="text-xs text-muted">{label}</span>
    </span>
  );
}
