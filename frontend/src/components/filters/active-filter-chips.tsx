"use client";

import { X } from "lucide-react";

export interface FilterChip {
  id: string;
  label: string;
  onRemove: () => void;
}

export function ActiveFilterChips({ chips, onClearAll }: { chips: FilterChip[]; onClearAll?: () => void }) {
  if (chips.length === 0) return null;
  return (
    <ul className="flex flex-wrap items-center gap-2" aria-label="Active filters">
      {chips.map((chip) => (
        <li key={chip.id} className="inline-flex items-center gap-1 rounded-full bg-accent-soft py-1 pl-3 pr-1.5 text-xs font-medium text-accent">
          {chip.label}
          <button type="button" onClick={chip.onRemove} aria-label={`Remove filter ${chip.label}`} className="rounded-full p-0.5 hover:bg-surface">
            <X className="size-3" aria-hidden />
          </button>
        </li>
      ))}
      {onClearAll && chips.length > 1 && (
        <li>
          <button type="button" onClick={onClearAll} className="text-xs font-medium text-muted underline-offset-2 hover:text-foreground hover:underline">
            Clear all
          </button>
        </li>
      )}
    </ul>
  );
}
