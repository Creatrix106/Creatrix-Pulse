import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { FinanceView } from "@/features/finance/finance-view";

export const metadata: Metadata = { title: getDashboardPage("finance").title };

export default function FinancePage() {
  return (
    <DashboardPage id="finance">
      <FinanceView />
    </DashboardPage>
  );
}
