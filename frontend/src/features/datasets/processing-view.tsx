"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Check, Circle, Loader2, XCircle } from "lucide-react";
import { ErrorState } from "@/components/feedback/error-state";
import { LoadingSkeleton } from "@/components/feedback/skeletons";
import { buttonStyles } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getDashboardHref } from "@/config/navigation";
import { useDataset, useProcessingStatus } from "@/hooks/use-datasets";
import { getErrorMessage } from "@/services/api-client";
import type { ProcessingStage } from "@/types/dataset";
import { cn } from "@/utils/cn";

function StageIcon({ status }: { status: ProcessingStage["status"] }) {
  if (status === "complete") return <span className="grid size-7 place-items-center rounded-full bg-success-soft text-success"><Check className="size-4" aria-hidden /></span>;
  if (status === "active") return <span className="grid size-7 place-items-center rounded-full bg-accent-soft text-accent"><Loader2 className="size-4 animate-spin" aria-hidden /></span>;
  if (status === "failed") return <span className="grid size-7 place-items-center rounded-full bg-danger-soft text-danger"><XCircle className="size-4" aria-hidden /></span>;
  return <span className="grid size-7 place-items-center rounded-full text-border-strong"><Circle className="size-4" aria-hidden /></span>;
}

export function ProcessingView({ datasetId }: { datasetId: string }) {
  const router = useRouter();
  const status = useProcessingStatus(datasetId);
  const dataset = useDataset(datasetId);
  const ready = status.data?.status === "ready";

  useEffect(() => {
    if (!ready) return;
    const timer = setTimeout(() => router.push(getDashboardHref(datasetId)), 1400);
    return () => clearTimeout(timer);
  }, [ready, router, datasetId]);

  if (status.isError) {
    return <ErrorState title="We couldn’t check processing status" message={getErrorMessage(status.error)} onRetry={() => status.refetch()} action={<Link href="/upload" className={buttonStyles()}>Upload again</Link>} />;
  }

  const data = status.data;
  const failed = data?.status === "failed";
  const hasProgress = typeof data?.progress === "number";

  return (
    <Card className="mx-auto max-w-xl p-6 sm:p-8">
      <p className="text-sm font-semibold uppercase tracking-wider text-accent">{failed ? "Processing failed" : ready ? "All done" : "Processing"}</p>
      <h1 className="mt-1 text-2xl font-bold tracking-tight text-emphasis">
        {ready ? "Your dashboard is ready" : failed ? "We couldn’t process this dataset" : "Preparing your dashboard"}
      </h1>
      <p className="mt-2 text-sm text-muted">{dataset.data ? `${dataset.data.name} · ${dataset.data.fileName}` : "Hang tight while we analyze your data."}</p>

      {!data ? (
        <div className="mt-8 space-y-4" role="status" aria-label="Loading status">
          {Array.from({ length: 5 }).map((_, i) => <LoadingSkeleton key={i} className="h-8 w-full" />)}
        </div>
      ) : (
        <ol className="mt-8 space-y-4" aria-live="polite">
          {data.stages.map((stage) => (
            <li key={stage.id} className="flex items-center gap-3" aria-current={stage.status === "active" ? "step" : undefined}>
              <StageIcon status={stage.status} />
              <span className={cn("text-sm", stage.status === "pending" ? "text-muted" : "font-medium text-emphasis", stage.status === "failed" && "text-danger")}>{stage.label}</span>
              {stage.status === "active" && <span className="text-xs text-muted">In progress…</span>}
            </li>
          ))}
        </ol>
      )}

      {hasProgress && data && (
        <div className="mt-6">
          <div className="h-2 overflow-hidden rounded-full bg-surface-accent" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={data.progress ?? 0} aria-label="Processing progress">
            <div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${data.progress}%` }} />
          </div>
          <p className="tabular mt-1 text-xs text-muted">{data.progress}% processed</p>
        </div>
      )}

      {failed && <p className="mt-6 rounded-md bg-danger-soft px-3 py-2.5 text-sm text-danger" role="alert">{data?.message ?? "Processing failed. Please upload the file again."}</p>}

      <div className="mt-8 flex flex-wrap gap-3">
        {ready && <Link href={getDashboardHref(datasetId)} className={buttonStyles()}>Open dashboard <ArrowRight className="size-4" aria-hidden /></Link>}
        {failed && <Link href={`/upload?replace=${datasetId}`} className={buttonStyles()}>Upload a corrected file</Link>}
        {!ready && !failed && <p className="text-xs text-muted">You can leave this page – processing continues in the background.</p>}
      </div>
    </Card>
  );
}
