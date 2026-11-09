import { CircleAlert } from "lucide-react";
import { cn } from "@/utils/cn";

export function InlineError({ message, className }: { message?: string; className?: string }) {
  if (!message) return null;
  return (
    <p role="alert" className={cn("flex items-start gap-2 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger", className)}>
      <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
      <span>{message}</span>
    </p>
  );
}
