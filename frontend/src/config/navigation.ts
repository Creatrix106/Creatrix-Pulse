import {
  BarChart3,
  Database,
  FileText,
  LayoutDashboard,
  Lightbulb,
  Package,
  Settings,
  Table2,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import type { UserRole } from "@/types/auth";

export type DashboardGroup = "analytics" | "workspace" | "manage";

export interface DashboardPageConfig {
  id: string;
  label: string;
  title: string;
  description: string;
  /** Route segment below /dashboard/[datasetId]. Empty string = overview. */
  segment: string;
  icon: LucideIcon;
  group: DashboardGroup;
  /** Whether the global date/comparison/filter bar is shown on this page. */
  showGlobalFilters: boolean;
  /** Optional role restriction (role-based UI permissions). Omit = everyone. */
  roles?: UserRole[];
}

/**
 * Adding a dashboard section:
 *  1. add an entry here
 *  2. create `app/dashboard/[datasetId]/<segment>/page.tsx`
 * Sidebar, mobile navigation and breadcrumbs update automatically.
 */
export const dashboardPages: DashboardPageConfig[] = [
  {
    id: "overview",
    label: "Overview",
    title: "Overview",
    description: "How your business is performing and what deserves attention.",
    segment: "",
    icon: LayoutDashboard,
    group: "analytics",
    showGlobalFilters: true,
  },
  {
    id: "sales",
    label: "Sales",
    title: "Sales Analytics",
    description: "Revenue, orders and units sold over time.",
    segment: "sales",
    icon: BarChart3,
    group: "analytics",
    showGlobalFilters: true,
  },
  {
    id: "products",
    label: "Products",
    title: "Product Analytics",
    description: "Best sellers, laggards and revenue contribution.",
    segment: "products",
    icon: Package,
    group: "analytics",
    showGlobalFilters: true,
  },
  {
    id: "customers",
    label: "Customers",
    title: "Customer Analytics",
    description: "Acquisition, retention and purchase behaviour.",
    segment: "customers",
    icon: Users,
    group: "analytics",
    showGlobalFilters: true,
  },
  {
    id: "finance",
    label: "Revenue & Cost",
    title: "Financial Analytics",
    description: "Revenue, costs, gross profit and margin.",
    segment: "finance",
    icon: Wallet,
    group: "analytics",
    showGlobalFilters: true,
  },
  {
    id: "explorer",
    label: "Data Explorer",
    title: "Data Explorer",
    description: "Search, sort, filter and export the underlying records.",
    segment: "explorer",
    icon: Table2,
    group: "workspace",
    showGlobalFilters: false,
  },
  {
    id: "insights",
    label: "Smart Insights",
    title: "Smart Insights",
    description: "Trends, anomalies and evidence-backed observations.",
    segment: "insights",
    icon: Lightbulb,
    group: "workspace",
    showGlobalFilters: true,
  },
  {
    id: "reports",
    label: "Reports",
    title: "Reports",
    description: "Build, preview and export performance reports.",
    segment: "reports",
    icon: FileText,
    group: "workspace",
    showGlobalFilters: false,
  },
  {
    id: "datasets",
    label: "Datasets",
    title: "Datasets",
    description: "Manage uploaded datasets and import history.",
    segment: "datasets",
    icon: Database,
    group: "manage",
    showGlobalFilters: false,
  },
  {
    id: "settings",
    label: "Settings",
    title: "Settings",
    description: "Profile, appearance and dashboard preferences.",
    segment: "settings",
    icon: Settings,
    group: "manage",
    showGlobalFilters: false,
  },
];

export const dashboardGroups: { id: DashboardGroup; label: string }[] = [
  { id: "analytics", label: "Analytics" },
  { id: "workspace", label: "Workspace" },
  { id: "manage", label: "Manage" },
];

export function getDashboardHref(datasetId: string, segment = ""): string {
  const base = `/dashboard/${datasetId}`;
  return segment ? `${base}/${segment}` : base;
}

export function getDashboardPage(id: string): DashboardPageConfig {
  const page = dashboardPages.find((p) => p.id === id);
  if (!page) throw new Error(`Unknown dashboard page: ${id}`);
  return page;
}

/** Resolves the page config for a pathname such as /dashboard/abc/sales. */
export function findPageByPathname(pathname: string, datasetId: string): DashboardPageConfig | undefined {
  const rest = pathname.replace(`/dashboard/${datasetId}`, "").replace(/^\//, "").split("/")[0] ?? "";
  return dashboardPages.find((p) => p.segment === rest);
}

export function canAccessPage(page: DashboardPageConfig, role: UserRole | undefined): boolean {
  if (!page.roles) return true;
  return role !== undefined && page.roles.includes(role);
}
