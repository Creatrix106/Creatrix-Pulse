import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { CustomersView } from "@/features/customers/customers-view";

export const metadata: Metadata = { title: getDashboardPage("customers").title };

export default function CustomersPage() {
  return (
    <DashboardPage id="customers">
      <CustomersView />
    </DashboardPage>
  );
}
