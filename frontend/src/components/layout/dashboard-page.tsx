import type { ReactNode } from "react";
import { getDashboardPage } from "@/config/navigation";
import { PageHeader } from "./page-header";

interface DashboardPageProps {
  /** Id from config/navigation.ts */
  id: string;
  actions?: ReactNode;
  children: ReactNode;
}

/** Server-rendered page frame: header text comes from the central navigation config. */
export function DashboardPage({ id, actions, children }: DashboardPageProps) {
  const page = getDashboardPage(id);
  return (
    <>
      <PageHeader title={page.title} description={page.description} actions={actions} />
      {children}
    </>
  );
}
