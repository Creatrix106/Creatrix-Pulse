"use client";

import { create } from "zustand";
import type { User } from "@/types/auth";

interface AuthState {
  user: User | null;
  setUser: (user: User | null) => void;
}

/** Session identity is restored from the backend; credentials remain in its httpOnly cookie. */
export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}));
