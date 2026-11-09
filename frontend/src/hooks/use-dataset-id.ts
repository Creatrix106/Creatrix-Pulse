"use client";

import { useParams } from "next/navigation";

export function useDatasetId(): string {
  const params = useParams<{ datasetId: string }>();
  return params.datasetId;
}
