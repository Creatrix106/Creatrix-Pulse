"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { PageSkeleton } from "@/components/feedback/skeletons";
import { buttonStyles } from "@/components/ui/button";
import { getDashboardHref } from "@/config/navigation";
import { useDatasets } from "@/hooks/use-datasets";

export function DashboardIndexView() {
  const router = useRouter();
  const datasets = useDatasets();
  const ready = datasets.data?.find((dataset) => dataset.status === "ready");

  useEffect(() => {
    if (ready) router.replace(getDashboardHref(ready.id));
  }, [ready, router]);

  if (datasets.isPending || ready) return <PageSkeleton />;
  if (datasets.isError) return <ErrorState title="We couldn’t load your datasets" message="Your dashboard list is temporarily unavailable." onRetry={() => datasets.refetch()} />;
  if (datasets.data.length === 0) {
    return <EmptyState title="No datasets yet" description="Upload a file to create your first analytics dashboard." icon={Upload} action={<Link href="/upload" className={buttonStyles()}>Upload dataset</Link>} />;
  }

  const processing = datasets.data.find((dataset) => !["ready", "failed"].includes(dataset.status));
  return (
    <EmptyState
      title={processing ? "Your dashboard is being prepared" : "No ready dashboards"}
      description={processing ? "Processing is still running for your latest dataset." : "Upload a corrected file or add a dataset to continue."}
      icon={Upload}
      action={<Link href={processing ? `/processing/${processing.id}` : "/upload"} className={buttonStyles()}>{processing ? "View processing" : "Upload dataset"}</Link>}
    />
  );
}
