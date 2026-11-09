"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { reportService } from "@/services/report.service";
import { getErrorMessage } from "@/services/api-client";
import { toast } from "@/stores/toast.store";
import type { ReportConfig } from "@/types/report";
import { useAuthStore } from "@/stores/auth.store";

export function useReportPreview(datasetId: string, config: ReportConfig) {
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useQuery({
    queryKey: ["reports", userId, datasetId, "preview", config.title, config.datePreset, [...config.metrics].sort().join(",")],
    queryFn: () => reportService.preview(datasetId, config),
    enabled: Boolean(userId && datasetId && config.metrics.length > 0),
  });
}

export function useReportHistory(datasetId: string) {
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useQuery({ queryKey: ["reports", userId, datasetId, "history"], queryFn: () => reportService.list(datasetId), enabled: Boolean(userId && datasetId) });
}

export function useCreateReport(datasetId: string) {
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useMutation({
    mutationFn: (config: ReportConfig) => reportService.create(datasetId, config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports", userId, datasetId, "history"] }),
    onError: (error) => toast.error("Could not generate report", getErrorMessage(error)),
  });
}
