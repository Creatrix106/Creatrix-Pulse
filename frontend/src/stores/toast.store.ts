"use client";

import { create } from "zustand";

export type ToastVariant = "success" | "error" | "info";

export interface ToastItem {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
}

interface ToastState {
  toasts: ToastItem[];
  push: (toast: Omit<ToastItem, "id">, durationMs?: number) => void;
  dismiss: (id: string) => void;
}

export const useToastStore = create<ToastState>()((set, get) => ({
  toasts: [],
  push: (toast, durationMs = 4500) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    set({ toasts: [...get().toasts, { ...toast, id }] });
    setTimeout(() => get().dismiss(id), durationMs);
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
}));

/** Imperative helper usable from hooks and event handlers. */
export const toast = {
  success: (title: string, description?: string) => useToastStore.getState().push({ variant: "success", title, description }),
  error: (title: string, description?: string) => useToastStore.getState().push({ variant: "error", title, description }, 7000),
  info: (title: string, description?: string) => useToastStore.getState().push({ variant: "info", title, description }),
};
