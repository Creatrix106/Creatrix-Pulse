"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { THEME_STORAGE_KEY, type ThemePreference } from "@/config/theme";

interface ThemeState {
  theme: ThemePreference;
  hydrated: boolean;
  setTheme: (theme: ThemePreference) => void;
}

/**
 * Persisted stores use `skipHydration` and are rehydrated in <StoreHydrator />
 * so server and first client render always agree (no hydration mismatches).
 */
export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: "light",
      hydrated: false,
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: THEME_STORAGE_KEY,
      skipHydration: true,
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => () => {
        useThemeStore.setState({ hydrated: true });
      },
    },
  ),
);
