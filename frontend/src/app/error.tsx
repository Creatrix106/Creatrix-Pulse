"use client";

import { ErrorState } from "@/components/feedback/error-state";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main id="main" className="grid min-h-screen place-items-center bg-surface-muted px-6">
      <ErrorState title="Something went wrong" message={error.message || "An unexpected error occurred."} onRetry={reset} className="max-w-lg" />
    </main>
  );
}
