"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRightLeft, FileSpreadsheet, RefreshCw, Trash2, Upload } from "lucide-react";
import { ChartCard } from "@/components/charts";
import { ConfirmDialog } from "@/components/feedback/confirm-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { QueryBoundary } from "@/components/feedback/query-boundary";
import { TableSkeleton } from "@/components/feedback/skeletons";
import { Badge } from "@/components/ui/badge";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ImportHistoryTable } from "@/components/upload/import-history-table";
import { getDashboardHref } from "@/config/navigation";
import { useDatasetId } from "@/hooks/use-dataset-id";
import { useDatasets, useDeleteDataset } from "@/hooks/use-datasets";
import type { Dataset } from "@/types/dataset";
import { formatBytes, formatDateTime } from "@/utils/format";
import { cn } from "@/utils/cn";
import { DatasetStatusBadge } from "./components/dataset-status-badge";

function DatasetCard({ dataset, active, onDelete }: { dataset: Dataset; active: boolean; onDelete: () => void }) {
  const caps = dataset.capabilities;
  return (
    <Card className={cn("flex flex-col p-5", active && "border-accent ring-1 ring-accent")}>
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-accent-soft text-accent"><FileSpreadsheet className="size-5" aria-hidden /></span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-emphasis">{dataset.name}</h3>
          <p className="truncate text-sm text-muted">{dataset.fileName}</p>
        </div>
        <DatasetStatusBadge status={dataset.status} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div><dt className="text-xs text-muted">Rows</dt><dd className="tabular font-medium">{dataset.rowCount.toLocaleString()}</dd></div>
        <div><dt className="text-xs text-muted">Columns</dt><dd className="tabular font-medium">{dataset.columnCount}</dd></div>
        <div><dt className="text-xs text-muted">Size</dt><dd className="font-medium">{formatBytes(dataset.fileSize)}</dd></div>
        <div><dt className="text-xs text-muted">Uploaded</dt><dd className="font-medium">{formatDateTime(dataset.uploadedAt)}</dd></div>
      </dl>
      {dataset.status === "failed" ? (
        <p className="mt-3 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">{dataset.errorMessage}</p>
      ) : (
        <div className="mt-3 flex flex-wrap gap-1.5">
          <Badge variant={caps.customers ? "accent" : "neutral"}>{caps.customers ? "Customer data" : "No customer data"}</Badge>
          <Badge variant={caps.cost ? "accent" : "neutral"}>{caps.cost ? "Cost data" : "No cost data"}</Badge>
          <Badge variant={caps.regions ? "accent" : "neutral"}>{caps.regions ? "Regions" : "No regions"}</Badge>
        </div>
      )}
      <div className="mt-5 flex flex-wrap gap-2 pt-1">
        {active ? (
          <Badge variant="success" className="h-8 px-3">Currently open</Badge>
        ) : dataset.status === "ready" ? (
          <Link href={getDashboardHref(dataset.id)} className={buttonStyles({ size: "sm" })}><ArrowRightLeft className="size-4" aria-hidden /> Switch to this</Link>
        ) : dataset.status !== "failed" ? (
          <Link href={`/processing/${dataset.id}`} className={buttonStyles({ size: "sm", variant: "secondary" })}>View progress</Link>
        ) : null}
        <Link href={`/upload?replace=${dataset.id}`} className={buttonStyles({ size: "sm", variant: "secondary" })}><RefreshCw className="size-4" aria-hidden /> Replace</Link>
        <Button size="sm" variant="ghost" onClick={onDelete} className="text-danger hover:bg-danger-soft"><Trash2 className="size-4" aria-hidden /> Delete</Button>
      </div>
    </Card>
  );
}

function DatasetsContent({ datasets }: { datasets: Dataset[] }) {
  const activeId = useDatasetId();
  const router = useRouter();
  const [pendingDelete, setPendingDelete] = useState<Dataset | null>(null);
  const remove = useDeleteDataset();

  if (datasets.length === 0) {
    return <EmptyState title="No datasets yet" description="Upload a CSV or Excel file to create your first dashboard." action={<Link href="/upload" className={buttonStyles()}><Upload className="size-4" aria-hidden /> Upload dataset</Link>} />;
  }

  const confirmDelete = () => {
    if (!pendingDelete) return;
    const target = pendingDelete;
    remove.mutate(target.id, {
      onSuccess: () => {
        setPendingDelete(null);
        if (target.id === activeId) {
          const next = datasets.find((d) => d.id !== target.id && d.status === "ready");
          router.push(next ? getDashboardHref(next.id, "datasets") : "/upload");
        }
      },
    });
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {datasets.map((d) => (
          <DatasetCard key={d.id} dataset={d} active={d.id === activeId} onDelete={() => setPendingDelete(d)} />
        ))}
      </div>
      <ChartCard title="Upload history" description="Every file imported into your workspace">
        <ImportHistoryTable datasets={datasets} />
      </ChartCard>
      <ConfirmDialog
        open={pendingDelete !== null}
        destructive
        title={`Delete “${pendingDelete?.name ?? ""}”?`}
        description="This removes the dataset and all dashboards built from it. This action cannot be undone."
        confirmLabel="Delete dataset"
        loading={remove.isPending}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

export function DatasetsView() {
  const query = useDatasets();
  return (
    <QueryBoundary query={query} loading={<TableSkeleton rows={5} columns={4} />}>
      {(datasets) => <DatasetsContent datasets={datasets} />}
    </QueryBoundary>
  );
}

export function UploadDatasetButton() {
  return (
    <Link href="/upload" className={buttonStyles()}>
      <Upload className="size-4" aria-hidden /> Upload dataset
    </Link>
  );
}
