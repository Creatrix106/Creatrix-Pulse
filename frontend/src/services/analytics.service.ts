import type {
  CustomersResponse,
  ExplorerData,
  FinanceResponse,
  OverviewData,
  ProductsData,
  SalesData,
} from "@/types/analytics";
import type { AnalyticsFilters } from "@/types/filters";
import type { Insight } from "@/types/insight";
import { apiClient } from "./api-client";

/**
 * BACKEND INTEGRATION POINT – analytics
 * All endpoints accept the AnalyticsFilters as query params:
 *   datePreset, dateFrom, dateTo, comparison, groupBy, categories (repeated), regions (repeated)
 *
 *   GET /datasets/:id/analytics/overview   -> OverviewData
 *   GET /datasets/:id/analytics/sales      -> SalesData
 *   GET /datasets/:id/analytics/products   -> ProductsData
 *   GET /datasets/:id/analytics/customers  -> CustomersResponse  (available:false when no customer column)
 *   GET /datasets/:id/analytics/finance    -> FinanceResponse    (available:false when no cost column)
 *   GET /datasets/:id/analytics/insights   -> Insight[]          (computed by the backend, never by the UI)
 *   GET /datasets/:id/records?limit=&offset= -> ExplorerData
 */
export interface AnalyticsService {
  getOverview(datasetId: string, filters: AnalyticsFilters): Promise<OverviewData>;
  getSales(datasetId: string, filters: AnalyticsFilters): Promise<SalesData>;
  getProducts(datasetId: string, filters: AnalyticsFilters): Promise<ProductsData>;
  getCustomers(datasetId: string, filters: AnalyticsFilters): Promise<CustomersResponse>;
  getFinance(datasetId: string, filters: AnalyticsFilters): Promise<FinanceResponse>;
  getInsights(datasetId: string, filters: AnalyticsFilters): Promise<Insight[]>;
  getExplorerData(datasetId: string, limit: number, offset: number, signal?: AbortSignal): Promise<ExplorerData>;
}

function toQuery(filters: AnalyticsFilters) {
  return {
    datePreset: filters.datePreset,
    dateFrom: filters.dateFrom,
    dateTo: filters.dateTo,
    comparison: filters.comparison,
    groupBy: filters.groupBy,
    categories: filters.categories,
    regions: filters.regions,
  };
}

const base = (id: string) => `/datasets/${encodeURIComponent(id)}`;

const httpAnalyticsService: AnalyticsService = {
  getOverview: (id, f) => apiClient.get<OverviewData>(`${base(id)}/analytics/overview`, { query: toQuery(f) }),
  getSales: (id, f) => apiClient.get<SalesData>(`${base(id)}/analytics/sales`, { query: toQuery(f) }),
  getProducts: (id, f) => apiClient.get<ProductsData>(`${base(id)}/analytics/products`, { query: toQuery(f) }),
  getCustomers: (id, f) => apiClient.get<CustomersResponse>(`${base(id)}/analytics/customers`, { query: toQuery(f) }),
  getFinance: (id, f) => apiClient.get<FinanceResponse>(`${base(id)}/analytics/finance`, { query: toQuery(f) }),
  getInsights: (id, f) => apiClient.get<Insight[]>(`${base(id)}/analytics/insights`, { query: toQuery(f) }),
  getExplorerData: (id, limit, offset, signal) => apiClient.get<ExplorerData>(`${base(id)}/records`, { query: { limit, offset }, signal }),
};

export const analyticsService: AnalyticsService = httpAnalyticsService;
