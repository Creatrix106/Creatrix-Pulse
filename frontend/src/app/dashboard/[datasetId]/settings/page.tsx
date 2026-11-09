import type { Metadata } from "next";
import { DashboardPage } from "@/components/layout/dashboard-page";
import { getDashboardPage } from "@/config/navigation";
import { SettingsView } from "@/features/settings/settings-view";

export const metadata: Metadata = { title: getDashboardPage("settings").title };

export default function SettingsPage() {
  return (
    <DashboardPage id="settings">
      <SettingsView />
    </DashboardPage>
  );
}
