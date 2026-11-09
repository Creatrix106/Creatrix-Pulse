"use client";

import { useEffect, useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastViewport } from "@/components/feedback/toast";
import { isApiError } from "@/services/api-client";
import { usePreferencesStore } from "@/stores/preferences.store";
import { useThemeStore } from "@/stores/theme.store";
import { useCurrentUser } from "@/hooks/use-auth";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        refetchOnWindowFocus: false,
        // Never retry client errors (4xx); retry transient failures twice.
        retry: (failureCount, error) => !(isApiError(error) && error.status >= 400 && error.status < 500) && failureCount < 2,
      },
    },
  });
}

/** Rehydrates persisted stores after mount (keeps SSR and first client render identical). */
function StoreHydrator() {
  useEffect(() => {
    void useThemeStore.persist.rehydrate();
    void usePreferencesStore.persist.rehydrate();
  }, []);
  return null;
}

function AuthSession() {
  useCurrentUser();
  return null;
}

/** Applies the `dark` class based on the stored preference (the inline script in layout prevents first-paint flash). */
function ThemeSync() {
  const theme = useThemeStore((s) => s.theme);
  const hydrated = useThemeStore((s) => s.hydrated);

  useEffect(() => {
    if (!hydrated) return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && media.matches);
      document.documentElement.classList.toggle("dark", dark);
    };
    apply();
    if (theme !== "system") return;
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme, hydrated]);

  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <StoreHydrator />
      <ThemeSync />
      <AuthSession />
      {children}
      <ToastViewport />
    </QueryClientProvider>
  );
}
