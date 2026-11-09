import { AlertTriangle, RotateCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  action?: ReactNode;
  className?: string;
}

export function ErrorState({ title = "We couldn’t load this", message = "Something went wrong while fetching your data.", onRetry, action, className }: ErrorStateProps) {
  return (
    <div role="alert" className={cn("flex flex-col items-center justify-center rounded-lg border border-border bg-surface px-6 py-12 text-center", className)}>
      <span className="mb-4 grid size-12 place-items-center rounded-full bg-danger-soft text-danger">
        <AlertTriangle className="size-6" aria-hidden />
      </span>
      <h3 className="text-base font-semibold text-emphasis">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-muted">{message}</p>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        {onRetry && (
          <Button variant="secondary" onClick={onRetry}>
            <RotateCw className="size-4" aria-hidden /> Try again
          </Button>
        )}
        {action}
      </div>
    </div>
  );
}
