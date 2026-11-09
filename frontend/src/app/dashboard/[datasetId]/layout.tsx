import type { ReactNode } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";

export default async function DatasetDashboardLayout({ children, params }: { children: ReactNode; params: Promise<{ datasetId: string }> }) {
  const { datasetId } = await params;
  return <DashboardLayout datasetId={datasetId}>{children}</DashboardLayout>;
}
