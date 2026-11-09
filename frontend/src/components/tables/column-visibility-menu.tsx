"use client";

import { Columns3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover } from "@/components/ui/popover";
import type { TableColumn } from "@/types/table";

interface ColumnVisibilityMenuProps<T> {
  columns: TableColumn<T>[];
  hidden: ReadonlySet<string>;
  onToggle: (key: string) => void;
}

export function ColumnVisibilityMenu<T>({ columns, hidden, onToggle }: ColumnVisibilityMenuProps<T>) {
  return (
    <Popover
      align="end"
      panelClassName="w-56 max-h-80 overflow-y-auto"
      trigger={({ open, toggle, panelId }) => (
        <Button variant="secondary" onClick={toggle} aria-expanded={open} aria-controls={panelId}>
          <Columns3 className="size-4" aria-hidden /> Columns
        </Button>
      )}
    >
      <fieldset>
        <legend className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-muted">Visible columns</legend>
        {columns.map((c) => {
          const visible = !hidden.has(c.key);
          return (
            <label key={c.key} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-surface-accent">
              <input
                type="checkbox"
                checked={visible}
                disabled={visible && columns.length - hidden.size <= 1}
                onChange={() => onToggle(c.key)}
                className="size-4 accent-[var(--accent)]"
              />
              {c.header}
            </label>
          );
        })}
      </fieldset>
    </Popover>
  );
}
