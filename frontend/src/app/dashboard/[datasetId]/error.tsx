"use client";

import { ErrorState } from "@/components/feedback/error-state";

export default function DashboardError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <ErrorState title="This page ran into a problem" message={error.message || "An unexpected error occurred."} onRetry={reset} />;
}
