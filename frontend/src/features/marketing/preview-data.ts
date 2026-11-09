import type { BreakdownItem, Kpi } from "@/types/analytics";

/** Illustrative figures used only by the marketing product preview – not real analytics. */
export const previewKpis: Kpi[] = [
  { id: "revenue", label: "Revenue", value: 482931, format: "currency", change: 12.3 },
  { id: "orders", label: "Orders", value: 1284, format: "number", change: 8.7 },
  { id: "units", label: "Units Sold", value: 3942, format: "number", change: 11.5 },
  { id: "profit", label: "Gross Profit", value: 142821, format: "currency", change: 10.9 },
  { id: "margin", label: "Profit Margin", value: 29.57, format: "percent", change: 2.4 },
];

export const previewTrend = [
  { date: "2026-01-01", revenue: 182000 },
  { date: "2026-02-01", revenue: 214000 },
  { date: "2026-03-01", revenue: 205000 },
  { date: "2026-04-01", revenue: 268000 },
  { date: "2026-05-01", revenue: 301000 },
  { date: "2026-06-01", revenue: 288000 },
  { date: "2026-07-01", revenue: 352000 },
  { date: "2026-08-01", revenue: 391000 },
  { date: "2026-09-01", revenue: 436000 },
  { date: "2026-10-01", revenue: 482000 },
];

export const previewProducts = [
  { name: "Product Alpha", units: 1240 },
  { name: "Product Beta", units: 860 },
  { name: "Product Gamma", units: 620 },
];

export const previewCategories: BreakdownItem[] = [
  { name: "Electronics", value: 38.3, share: 38.3 },
  { name: "Apparel", value: 24.7, share: 24.7 },
  { name: "Home & Living", value: 18.9, share: 18.9 },
  { name: "Others", value: 18.1, share: 18.1 },
];

export const previewRegions = [
  { name: "North", value: 180000 },
  { name: "South", value: 140000 },
  { name: "East", value: 90000 },
  { name: "West", value: 160000 },
];

export const previewNav = ["Overview", "Products", "Customers", "Revenue & Cost", "Comparisons", "Reports"];
