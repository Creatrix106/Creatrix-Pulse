import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { ProductsView } from "@/features/products/products-view";

export const metadata: Metadata = { title: getDashboardPage("products").title };

export default function ProductsPage() {
  return (
    <DashboardPage id="products">
      <ProductsView />
    </DashboardPage>
  );
}
