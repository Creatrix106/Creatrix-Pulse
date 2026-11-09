import type { DatePreset, MetricKey } from "./filters";

export type ReportFormat = "csv" | "json";

export interface ReportConfig {
  title: string;
  metrics: MetricKey[];
  datePreset: DatePreset;
  format: ReportFormat;
}

export interface ReportPreview {
  title: string;
  generatedAt: string;
  period: { from: string; to: string };
  summary: { label: string; value: number; format: "currency" | "number" | "percent" }[];
  columns: { key: string; label: string; format: "date" | "currency" | "number" }[];
  rows: Record<string, string | number>[];
}

export interface ReportRecord {
  id: string;
  datasetId: string;
  title: string;
  format: ReportFormat;
  createdAt: string;
  rowCount: number;
  sizeBytes: number;
  downloadUrl: string;
}
