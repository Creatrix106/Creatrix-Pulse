import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import type { ValidationIssue } from "@/types/dataset";
import { cn } from "@/utils/cn";

export function ValidationErrorList({ issues }: { issues: ValidationIssue[] }) {
  if (issues.length === 0) {
    return (
      <p className="flex items-center gap-2 rounded-md bg-success-soft px-3 py-2.5 text-sm font-medium text-success" role="status">
        <CheckCircle2 className="size-4" aria-hidden /> No validation issues found. You’re ready to upload.
      </p>
    );
  }
  const errors = issues.filter((i) => i.severity === "error");
  return (
    <div role={errors.length ? "alert" : "status"} className="space-y-2">
      <p className="text-sm font-medium text-emphasis">
        {errors.length > 0 ? `${errors.length} issue${errors.length > 1 ? "s" : ""} to fix before uploading` : "Review these warnings (you can still upload)"}
      </p>
      <ul className="space-y-1.5">
        {issues.map((issue) => {
          const isError = issue.severity === "error";
          const Icon = isError ? XCircle : AlertTriangle;
          return (
            <li key={issue.id} className={cn("flex items-start gap-2 rounded-md px-3 py-2 text-sm", isError ? "bg-danger-soft text-danger" : "bg-warning-soft text-warning")}>
              <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span><span className="sr-only">{isError ? "Error: " : "Warning: "}</span>{issue.message}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
