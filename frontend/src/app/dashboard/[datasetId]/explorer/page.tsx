import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { ExplorerView } from "@/features/data-explorer/explorer-view";

export const metadata: Metadata = { title: getDashboardPage("explorer").title };

export default function ExplorerPage() {
  return (
    <DashboardPage id="explorer">
      <ExplorerView />
    </DashboardPage>
  );
}
