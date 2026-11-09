import type { Metadata } from "next";
import { AppLayout } from "@/components/layout/app-layout";
import { ProcessingView } from "@/features/datasets/processing-view";
import { AuthGuard } from "@/components/auth/auth-guard";

export const metadata: Metadata = { title: "Processing dataset" };

export default async function ProcessingPage({ params }: { params: Promise<{ datasetId: string }> }) {
  const { datasetId } = await params;
  return (
    <AuthGuard><AppLayout width="md">
      <ProcessingView datasetId={datasetId} />
    </AppLayout></AuthGuard>
  );
}
