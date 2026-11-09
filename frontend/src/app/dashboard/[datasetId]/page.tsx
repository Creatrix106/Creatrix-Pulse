import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { OverviewView } from "@/features/overview/overview-view";

export const metadata: Metadata = { title: getDashboardPage("overview").title };

export default function OverviewPage() {
  return (
    <DashboardPage id="overview">
      <OverviewView />
    </DashboardPage>
  );
}
