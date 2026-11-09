import type { ReactNode } from "react";
import { Card, CardHeader } from "@/components/ui/card";
import { cn } from "@/utils/cn";

interface ChartCardProps {
  title: string;
  description?: string;
  /** Controls rendered in the header (selectors, toggles). */
  actions?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Consistent frame for every chart on the dashboard. */
export function ChartCard({ title, description, actions, footer, children, className }: ChartCardProps) {
  return (
    <Card className={cn("flex flex-col p-5", className)}>
      <CardHeader title={title} description={description} actions={actions} />
      <div className="mt-4 min-w-0 flex-1">{children}</div>
      {footer && <div className="mt-4 border-t border-border pt-3 text-sm text-muted">{footer}</div>}
    </Card>
  );
}
