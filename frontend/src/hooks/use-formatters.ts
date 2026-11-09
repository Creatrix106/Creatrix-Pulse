"use client";

import { useMemo } from "react";
import { usePreferencesStore } from "@/stores/preferences.store";
import { createFormatters, type Formatters } from "@/utils/format";

/** Formatters bound to the user's currency / locale preferences. */
export function useFormatters(): Formatters {
  const currency = usePreferencesStore((s) => s.currency);
  const locale = usePreferencesStore((s) => s.locale);
  return useMemo(() => createFormatters({ currency, locale }), [currency, locale]);
}
