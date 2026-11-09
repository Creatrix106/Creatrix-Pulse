"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { DEFAULT_CURRENCY } from "@/config/locale";
import { tableConfig } from "@/config/table";
import type { DatePreset } from "@/types/filters";

interface PreferencesState {
  currency: string;
  locale: string;
  defaultDatePreset: DatePreset;
  pageSize: number;
  showInsightsOnOverview: boolean;
  compactNumbers: boolean;
  update: (patch: Partial<Omit<PreferencesState, "update" | "reset">>) => void;
  reset: () => void;
}

const defaults = {
  currency: DEFAULT_CURRENCY.code,
  locale: DEFAULT_CURRENCY.locale,
  defaultDatePreset: "all" as DatePreset,
  pageSize: tableConfig.defaultPageSize as number,
  showInsightsOnOverview: true,
  compactNumbers: true,
};

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      ...defaults,
      update: (patch) => set(patch),
      reset: () => set(defaults),
    }),
    { name: "cp-preferences", skipHydration: true },
  ),
);
