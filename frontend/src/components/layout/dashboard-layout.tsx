"use client";

import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, Loader2, Upload } from "lucide-react";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { PageSkeleton } from "@/components/feedback/skeletons";
import { buttonStyles } from "@/components/ui/button";
import { findPageByPathname, getDashboardHref } from "@/config/navigation";
import { useDataset } from "@/hooks/use-datasets";
import { getErrorMessage, isApiError } from "@/services/api-client";
import { useFiltersStore } from "@/stores/filters.store";
import { usePreferencesStore } from "@/stores/preferences.store";
import { GlobalFilterBar } from "./global-filter-bar";
import { MobileNavigation } from "./mobile-navigation";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

/** Pages that stay reachable even when the dataset is not ready (so users can delete / replace it). */
const ALWAYS_AVAILABLE = new Set(["datasets", "settings"]);

function DatasetGate({ datasetId, children }: { datasetId: string; children: ReactNode }) {
  const pathname = usePathname();
  const query = useDataset(datasetId);
  const page = findPageByPathname(pathname, datasetId);

  if (query.isPending) return <PageSkeleton />;
  if (query.isError) {
    const notFound = isApiError(query.error) && query.error.status === 404;
    return (
      <ErrorState
        title={notFound ? "Dataset not found" : "We couldn’t load this dataset"}
        message={getErrorMessage(query.error)}
        onRetry={notFound ? undefined : () => query.refetch()}
        action={
          <Link href="/upload" className={buttonStyles({ variant: "primary" })}>
            <Upload className="size-4" aria-hidden /> Upload a dataset
          </Link>
        }
      />
    );
  }
  if (page && ALWAYS_AVAILABLE.has(page.id)) return <>{children}</>;

  const dataset = query.data;
  if (dataset.status === "failed") {
    return (
      <ErrorState
        title="This dataset failed to process"
        message={dataset.errorMessage ?? "Processing failed. Please upload the file again."}
        action={
          <Link href={getDashboardHref(datasetId, "datasets")} className={buttonStyles({ variant: "primary" })}>
            <Database className="size-4" aria-hidden /> Manage datasets
          </Link>
        }
      />
    );
  }
  if (dataset.status !== "ready") {
    return (
      <EmptyState
        icon={Loader2}
        title="Your dashboard is still being prepared"
        description="Analytics are generated once processing finishes."
        action={<Link href={`/processing/${datasetId}`} className={buttonStyles()}>View processing status</Link>}
      />
    );
  }
  return <>{children}</>;
}

/** Application chrome for /dashboard/[datasetId]/*: sidebar, topbar, global filters and content area. */
export function DashboardLayout({ datasetId, children }: { datasetId: string; children: ReactNode }) {
  useEffect(() => {
    // Reset filters when switching datasets; use the user's preferred default range.
    const apply = () => useFiltersStore.getState().reset(usePreferencesStore.getState().defaultDatePreset);
    if (usePreferencesStore.persist.hasHydrated()) {
      apply();
      return;
    }
    return usePreferencesStore.persist.onFinishHydration(apply);
  }, [datasetId]);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar datasetId={datasetId} />
      <MobileNavigation datasetId={datasetId} />
      <div className="lg:pl-[var(--sidebar-width)]">
        <Topbar datasetId={datasetId} />
        <GlobalFilterBar datasetId={datasetId} />
        <main id="main" className="mx-auto max-w-[var(--page-max-width)] px-[var(--space-page-x)] py-6 sm:py-8">
          <DatasetGate datasetId={datasetId}>{children}</DatasetGate>
        </main>
      </div>
    </div>
  );
}
