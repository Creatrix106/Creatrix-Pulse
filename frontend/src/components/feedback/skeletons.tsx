import { cn } from "@/utils/cn";
import { Card } from "@/components/ui/card";

export function LoadingSkeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded-md", className)} aria-hidden />;
}

export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <div role="status" aria-label="Loading chart" className="flex items-end gap-2" style={{ height }}>
      {[40, 65, 50, 80, 60, 90, 70, 95, 75, 85].map((h, i) => (
        <LoadingSkeleton key={i} className="flex-1" />
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 8, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div role="status" aria-label="Loading table" className="space-y-2">
      <LoadingSkeleton className="h-10 w-full" />
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-3">
          {Array.from({ length: columns }).map((__, c) => (
            <LoadingSkeleton key={c} className="h-8 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function KpiGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} className="space-y-3 p-5">
          <LoadingSkeleton className="h-4 w-24" />
          <LoadingSkeleton className="h-8 w-32" />
          <LoadingSkeleton className="h-4 w-20" />
        </Card>
      ))}
    </div>
  );
}

/** Generic page-level skeleton: KPI row + two chart cards. */
export function PageSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading page">
      <KpiGridSkeleton />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <LoadingSkeleton className="mb-4 h-5 w-40" />
          <ChartSkeleton />
        </Card>
        <Card className="p-5">
          <LoadingSkeleton className="mb-4 h-5 w-32" />
          <ChartSkeleton />
        </Card>
      </div>
    </div>
  );
}
