"use client";

import { motion } from "motion/react";
import { Card } from "@/components/ui/card";
import { useFormatters } from "@/hooks/use-formatters";
import type { Kpi } from "@/types/analytics";
import { cn } from "@/utils/cn";
import { ComparisonBadge } from "./trend-indicator";

interface KpiCardProps {
  kpi: Kpi;
  highlight?: boolean;
  index?: number;
}

export function KpiCard({ kpi, highlight, index = 0 }: KpiCardProps) {
  const f = useFormatters();
  const hasChange = kpi.change !== null && kpi.change !== undefined;
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, delay: index * 0.04 }}>
      <Card className={cn("h-full p-5", highlight && "border-transparent bg-surface-accent")}>
        <p className="text-sm font-medium text-muted">{kpi.label}</p>
        <p className="tabular mt-2 text-2xl font-semibold tracking-tight text-emphasis sm:text-[1.75rem]">{f.kpi(kpi.value, kpi.format)}</p>
        <div className="mt-2 min-h-5">
          {hasChange ? (
            <ComparisonBadge value={kpi.change as number} inverse={kpi.inverse} suffix={kpi.format === "percent" ? " pp" : "%"} label={kpi.format === "percent" ? "pts vs previous" : "vs previous period"} />
          ) : (
            <span className="text-xs text-muted">{kpi.hint ?? "No comparison selected"}</span>
          )}
        </div>
      </Card>
    </motion.div>
  );
}

export function KpiGrid({ kpis, className }: { kpis: Kpi[]; className?: string }) {
  if (kpis.length === 0) return null;
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2", kpis.length >= 5 ? "xl:grid-cols-3 2xl:grid-cols-6" : "xl:grid-cols-4", className)}>
      {kpis.map((kpi, i) => (
        <KpiCard key={kpi.id} kpi={kpi} index={i} highlight={i === 0} />
      ))}
    </div>
  );
}
