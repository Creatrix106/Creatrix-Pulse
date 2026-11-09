import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { DatasetsView, UploadDatasetButton } from "@/features/datasets/datasets-view";

export const metadata: Metadata = { title: getDashboardPage("datasets").title };

export default function DatasetsPage() {
  return (
    <DashboardPage id="datasets" actions={<UploadDatasetButton />}>
      <DatasetsView />
    </DashboardPage>
  );
}
