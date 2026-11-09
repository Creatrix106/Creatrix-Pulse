"use client";

import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { getErrorMessage } from "@/services/api-client";
import { ErrorState } from "./error-state";
import { PageSkeleton } from "./skeletons";

interface QueryBoundaryProps<T> {
  query: UseQueryResult<T>;
  loading?: ReactNode;
  children: (data: T) => ReactNode;
}

/** Standard loading / error / success handling for any TanStack Query result. */
export function QueryBoundary<T>({ query, loading, children }: QueryBoundaryProps<T>) {
  if (query.isPending) return <>{loading ?? <PageSkeleton />}</>;
  if (query.isError) return <ErrorState message={getErrorMessage(query.error)} onRetry={() => query.refetch()} />;
  return (
    <div className={query.isFetching ? "opacity-70 transition-opacity" : "transition-opacity"} aria-busy={query.isFetching}>
      {children(query.data)}
    </div>
  );
}
