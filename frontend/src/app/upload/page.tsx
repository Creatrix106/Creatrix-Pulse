import type { Metadata } from "next";
import { AppLayout } from "@/components/layout/app-layout";
import { UploadView } from "@/features/datasets/upload-view";
import { AuthGuard } from "@/components/auth/auth-guard";

export const metadata: Metadata = { title: "Upload dataset" };

export default async function UploadPage({ searchParams }: { searchParams: Promise<{ replace?: string }> }) {
  const { replace } = await searchParams;
  return (
    <AuthGuard><AppLayout width="lg">
      <UploadView replaceDatasetId={replace} />
    </AppLayout></AuthGuard>
  );
}
