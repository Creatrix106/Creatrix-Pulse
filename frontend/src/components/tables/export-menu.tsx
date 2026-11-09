"use client";

import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover } from "@/components/ui/popover";
import { featureFlags } from "@/config/features";

export type ExportFormat = "csv" | "json";

interface ExportMenuProps {
  onExport: (format: ExportFormat) => void;
  disabled?: boolean;
  /** Describes what will be exported, e.g. "1,204 filtered rows". */
  description?: string;
}

/** Export options. Formats the backend does not support yet are shown as unavailable. */
export function ExportMenu({ onExport, disabled, description }: ExportMenuProps) {
  const item = "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-surface-accent disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent";
  return (
    <Popover
      align="end"
      panelClassName="w-60"
      trigger={({ open, toggle, panelId }) => (
        <Button variant="secondary" onClick={toggle} disabled={disabled} aria-expanded={open} aria-controls={panelId}>
          <Download className="size-4" aria-hidden /> Export
        </Button>
      )}
    >
      {(close) => (
        <div>
          {description && <p className="px-3 pb-1 pt-0.5 text-xs text-muted">{description}</p>}
          <button type="button" className={item} onClick={() => { onExport("csv"); close(); }}>CSV (.csv)</button>
          <button type="button" className={item} onClick={() => { onExport("json"); close(); }}>JSON (.json)</button>
          <button type="button" className={item} disabled={!featureFlags.xlsxExport}>
            Excel (.xlsx) <span className="text-xs text-muted">Unavailable</span>
          </button>
        </div>
      )}
    </Popover>
  );
}
