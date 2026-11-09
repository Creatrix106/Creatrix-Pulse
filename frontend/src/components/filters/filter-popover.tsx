"use client";

import { ListFilter } from "lucide-react";
import { Popover } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

export interface FilterGroup {
  id: string;
  label: string;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

interface FilterPopoverProps {
  groups: FilterGroup[];
  label?: string;
}

/** Multi-select filter groups (e.g. category, region) inside a popover. */
export function FilterPopover({ groups, label = "Filters" }: FilterPopoverProps) {
  const activeCount = groups.reduce((n, g) => n + g.selected.length, 0);
  const visible = groups.filter((g) => g.options.length > 0);

  return (
    <Popover
      panelClassName="w-72 max-h-96 overflow-y-auto p-3"
      trigger={({ open, toggle, panelId }) => (
        <Button size="sm" variant="secondary" onClick={toggle} aria-expanded={open} aria-controls={panelId}>
          <ListFilter className="size-4" aria-hidden /> {label}
          {activeCount > 0 && <span className="rounded-full bg-primary px-1.5 text-xs text-primary-foreground">{activeCount}</span>}
        </Button>
      )}
    >
      {visible.length === 0 ? (
        <p className="p-2 text-sm text-muted">This dataset has no category or region columns to filter by.</p>
      ) : (
        <div className="space-y-4">
          {visible.map((group) => (
            <fieldset key={group.id}>
              <legend className="mb-1.5 flex w-full items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted">
                {group.label}
                {group.selected.length > 0 && (
                  <button type="button" className="font-medium normal-case text-accent hover:underline" onClick={() => group.onChange([])}>Clear</button>
                )}
              </legend>
              <div className="space-y-0.5">
                {group.options.map((option) => {
                  const checked = group.selected.includes(option);
                  return (
                    <label key={option} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-surface-accent">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => group.onChange(checked ? group.selected.filter((s) => s !== option) : [...group.selected, option])}
                        className="size-4 accent-[var(--accent)]"
                      />
                      {option}
                    </label>
                  );
                })}
              </div>
            </fieldset>
          ))}
        </div>
      )}
    </Popover>
  );
}
