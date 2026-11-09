"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** False during SSR and hydration, true afterwards. Use for UI that depends on browser-only state. */
export function useMounted(): boolean {
  return useSyncExternalStore(subscribe, () => true, () => false);
}
