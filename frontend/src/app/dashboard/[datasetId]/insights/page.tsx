import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { InsightsView } from "@/features/insights/insights-view";

export const metadata: Metadata = { title: getDashboardPage("insights").title };

export default function InsightsPage() {
  return (
    <DashboardPage id="insights">
      <InsightsView />
    </DashboardPage>
  );
}
