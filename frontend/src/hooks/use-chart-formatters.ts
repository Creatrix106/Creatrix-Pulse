"use client";

import { useMemo } from "react";
import { usePreferencesStore } from "@/stores/preferences.store";
import type { GroupBy } from "@/types/filters";
import { useFormatters } from "./use-formatters";

/** Formatter bundle for charts: currency/number axes plus period labels for the active grouping. */
export function useChartFormatters(groupBy: GroupBy = "month") {
  const f = useFormatters();
  const compact = usePreferencesStore((s) => s.compactNumbers);
  return useMemo(
    () => ({
      currency: (v: number) => f.currency(v),
      currencyAxis: (v: number) => f.currency(v, { compact: true }),
      number: (v: number) => f.number(v),
      numberAxis: (v: number) => (compact ? f.compact(v) : f.number(v)),
      percent: (v: number) => f.percent(v),
      percentAxis: (v: number) => `${v}%`,
      xFormatter: (v: string) => f.period(v, groupBy),
      tooltipLabel: (v: string) => f.period(v, groupBy, "long"),
    }),
    [f, compact, groupBy],
  );
}
