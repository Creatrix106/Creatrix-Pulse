import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { SalesView } from "@/features/sales/sales-view";

export const metadata: Metadata = { title: getDashboardPage("sales").title };

export default function SalesPage() {
  return (
    <DashboardPage id="sales">
      <SalesView />
    </DashboardPage>
  );
}
