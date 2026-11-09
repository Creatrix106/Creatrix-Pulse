import type { Capability } from "./api";
import type { Insight } from "./insight";

export type KpiFormat = "currency" | "number" | "percent";

export interface Kpi {
  id: string;
  label: string;
  value: number;
  format: KpiFormat;
  /** Percent change vs comparison period (percentage points for percent KPIs). null/undefined = no comparison. */
  change?: number | null;
  /** True when a decrease is good (e.g. costs). */
  inverse?: boolean;
  hint?: string;
}

export interface TimeSeriesPoint {
  /** Bucket start, ISO date YYYY-MM-DD. */
  date: string;
  revenue: number;
  orders: number;
  units: number;
  aov: number;
  /** Only present when the dataset has cost information. */
  cost?: number;
  profit?: number;
  margin?: number;
}

export interface BreakdownItem {
  name: string;
  value: number;
  /** Share of total, 0-100. */
  share: number;
  change?: number | null;
  secondary?: number;
}

export interface ProductPerformance {
  id: string;
  name: string;
  category: string;
  revenue: number;
  units: number;
  orders: number;
  share: number;
  change?: number | null;
  margin?: number | null;
}

export interface DatePeriod {
  from: string;
  to: string;
}

export interface OverviewData {
  period: DatePeriod;
  kpis: Kpi[];
  revenueTrend: TimeSeriesPoint[];
  topProducts: ProductPerformance[];
  categories: BreakdownItem[];
  regions: BreakdownItem[];
  insights: Insight[];
}

export interface SalesData {
  kpis: Kpi[];
  trend: TimeSeriesPoint[];
  previousTrend: TimeSeriesPoint[] | null;
  categories: BreakdownItem[];
  regions: BreakdownItem[];
  categoryNames: string[];
  categoryTrend: { date: string; values: Record<string, number> }[];
}

export interface ProductsData {
  top: ProductPerformance[];
  low: ProductPerformance[];
  all: ProductPerformance[];
  categories: BreakdownItem[];
}

export interface CustomerSegment {
  name: string;
  description: string;
  customers: number;
  revenue: number;
  share: number;
}

export interface CustomersData {
  kpis: Kpi[];
  newVsReturning: { date: string; newCustomers: number; returningCustomers: number }[];
  distribution: BreakdownItem[];
  frequency: { label: string; count: number }[];
  segments: CustomerSegment[];
}

export interface FinanceData {
  kpis: Kpi[];
  trend: TimeSeriesPoint[];
  categoryMargins: BreakdownItem[];
}

export interface ExplorerColumn {
  key: string;
  label: string;
  type: "string" | "number" | "date";
  /** Display hint for numeric columns. */
  format?: "currency";
}

export type ExplorerRow = Record<string, string | number | null>;

export interface ExplorerData {
  columns: ExplorerColumn[];
  rows: ExplorerRow[];
  /** Total rows matching the request, supplied by the records endpoint. */
  total: number;
}

export type CustomersResponse = Capability<CustomersData>;
export type FinanceResponse = Capability<FinanceData>;
