import { BarChart3 } from "lucide-react";

export function EmptyChartState({ message = "No data available for the selected filters.", height = 240 }: { message?: string; height?: number }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md bg-surface-muted text-center text-sm text-muted" style={{ minHeight: height }}>
      <BarChart3 className="size-6 opacity-60" aria-hidden />
      <p className="max-w-xs px-4">{message}</p>
    </div>
  );
}
