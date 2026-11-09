"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { analyticsService } from "@/services/analytics.service";
import type { AnalyticsFilters } from "@/types/filters";
import { useAnalyticsFilters } from "./use-analytics-filters";
import { useDatasetId } from "./use-dataset-id";
import { useAuthStore } from "@/stores/auth.store";

/**
 * One hook per analytics endpoint. The dataset id (from the route) and the global
 * filters are part of the query key, so changing either refetches automatically.
 */
function useAnalyticsQuery<T>(name: string, fetcher: (datasetId: string, filters: AnalyticsFilters) => Promise<T>) {
  const datasetId = useDatasetId();
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const filters = useAnalyticsFilters();
  return useQuery({
    queryKey: ["analytics", userId, datasetId, name, filters],
    queryFn: () => fetcher(datasetId, filters),
    placeholderData: keepPreviousData,
    enabled: Boolean(userId && datasetId),
  });
}

export const useOverviewQuery = () => useAnalyticsQuery("overview", (id, f) => analyticsService.getOverview(id, f));
export const useSalesQuery = () => useAnalyticsQuery("sales", (id, f) => analyticsService.getSales(id, f));
export const useProductsQuery = () => useAnalyticsQuery("products", (id, f) => analyticsService.getProducts(id, f));
export const useCustomersQuery = () => useAnalyticsQuery("customers", (id, f) => analyticsService.getCustomers(id, f));
export const useFinanceQuery = () => useAnalyticsQuery("finance", (id, f) => analyticsService.getFinance(id, f));
export const useInsightsQuery = () => useAnalyticsQuery("insights", (id, f) => analyticsService.getInsights(id, f));

export function useExplorerQuery(page: number, pageSize: number) {
  const datasetId = useDatasetId();
  const userId = useAuthStore((s) => s.user?.id ?? null);
  return useQuery({
    queryKey: ["analytics", userId, datasetId, "explorer", page, pageSize],
    queryFn: ({ signal }) => analyticsService.getExplorerData(datasetId, pageSize, page * pageSize, signal),
    enabled: Boolean(userId && datasetId),
  });
}
