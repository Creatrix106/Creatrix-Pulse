"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authService } from "@/services/auth.service";
import { useAuthStore } from "@/stores/auth.store";
import { isApiError } from "@/services/api-client";
import { toast } from "@/stores/toast.store";
import type { User } from "@/types/auth";

export const authKey = ["auth", "me"] as const;

async function clearPrivateCache(queryClient: ReturnType<typeof useQueryClient>) {
  await queryClient.cancelQueries();
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
}

function sameIdentity(a: User | null | undefined, b: User | null | undefined) {
  return a?.id === b?.id;
}

export function useCurrentUser() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useQuery({
    queryKey: authKey,
    queryFn: async ({ signal }) => {
      try {
        const user = await authService.me(signal);
        const previous = useAuthStore.getState().user;
        if (previous && !sameIdentity(previous, user)) await clearPrivateCache(queryClient);
        setUser(user);
        return user;
      } catch (error) {
        if (isApiError(error) && error.status === 401) {
          await clearPrivateCache(queryClient);
          setUser(null);
        }
        throw error;
      }
    },
    retry: (count, error) => !(isApiError(error) && error.status >= 400 && error.status < 500) && count < 2,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.login,
    onMutate: () => queryClient.cancelQueries({ queryKey: authKey, exact: true }),
    onSuccess: async (user) => {
      const previous = useAuthStore.getState().user;
      if (!sameIdentity(previous, user)) await clearPrivateCache(queryClient);
      setUser(user);
      queryClient.setQueryData(authKey, user);
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.register,
    onMutate: () => queryClient.cancelQueries({ queryKey: authKey, exact: true }),
    onSuccess: async (user) => {
      await clearPrivateCache(queryClient);
      setUser(user);
      queryClient.setQueryData(authKey, user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: authService.logout,
    onMutate: () => queryClient.cancelQueries({ queryKey: authKey, exact: true }),
    onSettled: async () => {
      // Even if the server is unreachable, stop displaying data from the signed-out UI.
      await clearPrivateCache(queryClient);
      setUser(null);
      queryClient.setQueryData(authKey, null);
    },
    onError: () => toast.error("Could not sign out", "Please try again."),
  });
}
