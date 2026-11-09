"use client";

import { usePathname, useRouter } from "next/navigation";
import { Menu } from "lucide-react";
import { DatasetSelector } from "@/components/filters/option-selectors";
import { findPageByPathname, getDashboardHref } from "@/config/navigation";
import { useDataset, useDatasets } from "@/hooks/use-datasets";
import { useUiStore } from "@/stores/ui.store";
import { Breadcrumbs, type BreadcrumbItem } from "./breadcrumbs";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";

export function Topbar({ datasetId }: { datasetId: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);
  const { data: datasets } = useDatasets();
  const { data: dataset } = useDataset(datasetId);
  const page = findPageByPathname(pathname, datasetId);

  const crumbs: BreadcrumbItem[] = [
    { label: "Dashboard", href: getDashboardHref(datasetId) },
    { label: dataset?.name ?? "Dataset" },
    ...(page && page.segment !== "" ? [{ label: page.label }] : []),
  ];

  return (
    <header className="sticky top-0 z-30 flex h-[var(--topbar-height)] items-center gap-3 border-b border-border bg-background/90 px-[var(--space-page-x)] backdrop-blur">
      <button type="button" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation" className="-ml-2 grid size-10 place-items-center rounded-md text-foreground hover:bg-surface-accent lg:hidden">
        <Menu className="size-5" aria-hidden />
      </button>
      <div className="hidden min-w-0 flex-1 sm:block">
        <Breadcrumbs items={crumbs} />
      </div>
      <div className="ml-auto flex items-center gap-2 sm:ml-0">
        <DatasetSelector
          datasets={datasets ?? (dataset ? [dataset] : [])}
          value={datasetId}
          onChange={(id) => router.push(getDashboardHref(id, page?.segment ?? ""))}
          className="w-44 sm:w-60"
        />
        <ThemeToggle />
        <UserMenu datasetId={datasetId} />
      </div>
    </header>
  );
}
