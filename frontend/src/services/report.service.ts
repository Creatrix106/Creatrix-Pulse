import type { ReportConfig, ReportPreview, ReportRecord } from "@/types/report";
import { apiClient } from "./api-client";

/**
 * BACKEND INTEGRATION POINT – reports
 *   POST /datasets/:id/reports/preview  (ReportConfig) -> ReportPreview
 *   GET  /datasets/:id/reports                          -> ReportRecord[]  (download history)
 *   POST /datasets/:id/reports          (ReportConfig) -> ReportRecord     (include `downloadUrl`)
 */
export interface ReportService {
  preview(datasetId: string, config: ReportConfig): Promise<ReportPreview>;
  list(datasetId: string): Promise<ReportRecord[]>;
  create(datasetId: string, config: ReportConfig): Promise<ReportRecord>;
}

const base = (id: string) => `/datasets/${encodeURIComponent(id)}/reports`;

const httpReportService: ReportService = {
  preview: (id, config) => apiClient.post<ReportPreview>(`${base(id)}/preview`, config),
  list: (id) => apiClient.get<ReportRecord[]>(base(id)),
  create: (id, config) => apiClient.post<ReportRecord>(base(id), config),
};

export const reportService: ReportService = httpReportService;
