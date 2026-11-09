import type { AnalyticsFilters, ComparisonMode, DatePreset, GroupBy, MetricKey } from "@/types/filters";

export const DATE_PRESETS: { value: DatePreset; label: string; days?: number }[] = [
  { value: "all", label: "All time" },
  { value: "last_30d", label: "Last 30 days", days: 30 },
  { value: "last_90d", label: "Last 90 days", days: 90 },
  { value: "last_180d", label: "Last 180 days", days: 180 },
  { value: "ytd", label: "Year to date" },
  { value: "custom", label: "Custom range" },
];

export const COMPARISON_OPTIONS: { value: ComparisonMode; label: string }[] = [
  { value: "none", label: "No comparison" },
  { value: "previous_period", label: "Previous period" },
];

export const GROUP_BY_OPTIONS: { value: GroupBy; label: string }[] = [
  { value: "day", label: "Daily" },
  { value: "week", label: "Weekly" },
  { value: "month", label: "Monthly" },
];

export const METRIC_OPTIONS: {
  value: MetricKey;
  label: string;
  format: "currency" | "number";
  requiresCost?: boolean;
}[] = [
  { value: "revenue", label: "Revenue", format: "currency" },
  { value: "orders", label: "Orders", format: "number" },
  { value: "units", label: "Units sold", format: "number" },
  { value: "aov", label: "Average order value", format: "currency" },
  { value: "cost", label: "Cost", format: "currency", requiresCost: true },
  { value: "profit", label: "Gross profit", format: "currency", requiresCost: true },
];

export const DEFAULT_FILTERS: AnalyticsFilters = {
  datePreset: "all",
  comparison: "none",
  groupBy: "month",
  categories: [],
  regions: [],
};

/** Preferred bucket size for each preset. */
export const PRESET_GROUP_BY: Record<DatePreset, GroupBy> = {
  all: "month",
  last_30d: "day",
  last_90d: "week",
  last_180d: "week",
  ytd: "month",
  custom: "week",
};
