"use client";

import { create } from "zustand";
import { DEFAULT_FILTERS, PRESET_GROUP_BY } from "@/config/filters";
import type { AnalyticsFilters, ComparisonMode, DatePreset, GroupBy } from "@/types/filters";

interface FiltersState extends AnalyticsFilters {
  setDatePreset: (preset: DatePreset) => void;
  setCustomRange: (from: string, to: string) => void;
  setComparison: (mode: ComparisonMode) => void;
  setGroupBy: (groupBy: GroupBy) => void;
  setCategories: (categories: string[]) => void;
  setRegions: (regions: string[]) => void;
  reset: (preset?: DatePreset) => void;
}

/** Global analytics filters shared by every dashboard page. Part of each query key. */
export const useFiltersStore = create<FiltersState>()((set) => ({
  ...DEFAULT_FILTERS,
  setDatePreset: (datePreset) =>
    set({ datePreset, groupBy: PRESET_GROUP_BY[datePreset], ...(datePreset !== "custom" && { dateFrom: undefined, dateTo: undefined }) }),
  setCustomRange: (dateFrom, dateTo) =>
    set({ datePreset: "custom", dateFrom, dateTo, groupBy: PRESET_GROUP_BY.custom }),
  setComparison: (comparison) => set({ comparison }),
  setGroupBy: (groupBy) => set({ groupBy }),
  setCategories: (categories) => set({ categories }),
  setRegions: (regions) => set({ regions }),
  reset: (preset = "all") =>
    set({ ...DEFAULT_FILTERS, datePreset: preset, groupBy: PRESET_GROUP_BY[preset] }),
}));
