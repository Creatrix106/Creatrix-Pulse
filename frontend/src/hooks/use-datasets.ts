"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { datasetService } from "@/services/dataset.service";
import { getErrorMessage, isApiError } from "@/services/api-client";
import { toast } from "@/stores/toast.store";
import type { UploadRequest } from "@/types/dataset";
import { useAuthStore } from "@/stores/auth.store";

export const datasetKeys = {
  all: (userId: string | null) => ["datasets", userId] as const,
  detail: (userId: string | null, id: string) => ["datasets", userId, id] as const,
  processing: (userId: string | null, id: string) => ["datasets", userId, id, "processing"] as const,
};

export function useDatasets() {
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useQuery({ queryKey: datasetKeys.all(userId), queryFn: () => datasetService.list(), enabled: Boolean(userId) });
}

export function useDataset(id: string) {
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useQuery({
    queryKey: datasetKeys.detail(userId, id),
    queryFn: () => datasetService.get(id),
    enabled: Boolean(userId && id),
    retry: (count, error) => !(isApiError(error) && error.status < 500 && error.status > 0) && count < 2,
  });
}

/** Polls processing status until the dataset is ready or has failed. */
export function useProcessingStatus(id: string) {
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useQuery({
    queryKey: datasetKeys.processing(userId, id),
    queryFn: () => datasetService.getProcessingStatus(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "ready" || status === "failed" ? false : 1200;
    },
    enabled: Boolean(userId && id),
  });
}

export function useDeleteDataset() {
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useMutation({
    mutationFn: (id: string) => datasetService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.all(userId) });
      toast.success("Dataset deleted");
    },
    onError: (error) => toast.error("Could not delete dataset", getErrorMessage(error)),
  });
}

export function useUploadDataset(onProgress?: (percent: number) => void) {
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useMutation({
    mutationFn: (request: UploadRequest) => datasetService.upload(request, onProgress),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: datasetKeys.all(userId) }),
  });
}
