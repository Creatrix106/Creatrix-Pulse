import { Badge, type BadgeVariant } from "@/components/ui/badge";
import type { DatasetStatus } from "@/types/dataset";

const config: Record<DatasetStatus, { label: string; variant: BadgeVariant }> = {
  uploading: { label: "Uploading", variant: "accent" },
  validating: { label: "Validating", variant: "accent" },
  processing: { label: "Processing", variant: "accent" },
  generating: { label: "Generating analytics", variant: "accent" },
  ready: { label: "Ready", variant: "success" },
  failed: { label: "Failed", variant: "danger" },
};

export function DatasetStatusBadge({ status }: { status: DatasetStatus }) {
  const { label, variant } = config[status];
  return <Badge variant={variant}>{label}</Badge>;
}
