"use client";

import { useShallow } from "zustand/react/shallow";
import { useFiltersStore } from "@/stores/filters.store";
import type { AnalyticsFilters } from "@/types/filters";

/** Current global filters as a plain object (stable between renders unless a field changes). */
export function useAnalyticsFilters(): AnalyticsFilters {
  return useFiltersStore(
    useShallow((s) => ({
      datePreset: s.datePreset,
      dateFrom: s.dateFrom,
      dateTo: s.dateTo,
      comparison: s.comparison,
      groupBy: s.groupBy,
      categories: s.categories,
      regions: s.regions,
    })),
  );
}
