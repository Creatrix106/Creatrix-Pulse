import { AlertTriangle, Eye, Lightbulb, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";
import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Insight, InsightType } from "@/types/insight";

export const insightTypeConfig: Record<InsightType, { label: string; icon: LucideIcon; badge: BadgeVariant; tone: string }> = {
  positive: { label: "Positive trend", icon: TrendingUp, badge: "success", tone: "bg-success-soft text-success" },
  negative: { label: "Negative trend", icon: TrendingDown, badge: "danger", tone: "bg-danger-soft text-danger" },
  anomaly: { label: "Anomaly", icon: AlertTriangle, badge: "warning", tone: "bg-warning-soft text-warning" },
  observation: { label: "Observation", icon: Eye, badge: "accent", tone: "bg-accent-soft text-accent" },
  recommendation: { label: "Recommendation", icon: Lightbulb, badge: "accent", tone: "bg-accent-soft text-accent" },
};

interface InsightCardProps {
  insight: Insight;
  /** Compact variant hides the evidence list (used on the overview). */
  compact?: boolean;
}

export function InsightCard({ insight, compact }: InsightCardProps) {
  const config = insightTypeConfig[insight.type];
  const Icon = config.icon;
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 grid size-9 shrink-0 place-items-center rounded-md ${config.tone}`}>
          <Icon className="size-[18px]" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <Badge variant={config.badge} className="mb-1.5">{config.label}</Badge>
          <h4 className="text-sm font-semibold leading-snug text-emphasis">{insight.title}</h4>
          {!compact && <p className="mt-1 text-sm text-muted">{insight.summary}</p>}
          {!compact && insight.evidence.length > 0 && (
            <dl className="mt-3 grid gap-x-6 gap-y-1.5 rounded-md bg-surface-muted p-3 text-sm sm:grid-cols-2">
              {insight.evidence.map((e) => (
                <div key={e.label} className="flex justify-between gap-3">
                  <dt className="text-muted">{e.label}</dt>
                  <dd className="tabular font-medium text-foreground">{e.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>
    </Card>
  );
}
