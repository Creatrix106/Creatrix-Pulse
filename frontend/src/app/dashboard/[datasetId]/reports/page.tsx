import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { ReportsView } from "@/features/reports/reports-view";

export const metadata: Metadata = { title: getDashboardPage("reports").title };

export default function ReportsPage() {
  return (
    <DashboardPage id="reports">
      <ReportsView />
    </DashboardPage>
  );
}
