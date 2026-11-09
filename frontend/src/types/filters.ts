export type DatePreset = "all" | "last_30d" | "last_90d" | "last_180d" | "ytd" | "custom";
export type ComparisonMode = "none" | "previous_period";
export type GroupBy = "day" | "week" | "month";
export type MetricKey = "revenue" | "orders" | "units" | "aov" | "cost" | "profit";

/** Global filters sent with every analytics request. */
export interface AnalyticsFilters {
  datePreset: DatePreset;
  /** ISO date (YYYY-MM-DD). Only used when datePreset is "custom". */
  dateFrom?: string;
  dateTo?: string;
  comparison: ComparisonMode;
  groupBy: GroupBy;
  categories: string[];
  regions: string[];
}
