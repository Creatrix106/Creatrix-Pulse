"use client";

import { Dialog } from "@/components/ui/dialog";

export interface DetailField {
  label: string;
  value: string;
}

interface RowDetailsDrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  fields: DetailField[];
}

export function RowDetailsDrawer({ open, onClose, title, description, fields }: RowDetailsDrawerProps) {
  return (
    <Dialog open={open} onClose={onClose} title={title} description={description} placement="right">
      <dl className="divide-y divide-border">
        {fields.map((f) => (
          <div key={f.label} className="flex justify-between gap-4 py-3 text-sm">
            <dt className="text-muted">{f.label}</dt>
            <dd className="tabular break-words text-right font-medium text-foreground">{f.value || "—"}</dd>
          </div>
        ))}
      </dl>
    </Dialog>
  );
}
