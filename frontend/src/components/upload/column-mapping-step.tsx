"use client";

import { Select } from "@/components/ui/select";
import { CANONICAL_FIELDS } from "@/config/files";
import type { CanonicalField, ColumnMapping, DatasetProfile } from "@/types/dataset";

interface ColumnMappingStepProps {
  profile: DatasetProfile;
  mapping: ColumnMapping;
  onChange: (field: CanonicalField, column: string | undefined) => void;
}

/** Lets the user map uploaded columns to the business fields the analytics engine understands. */
export function ColumnMappingStep({ profile, mapping, onChange }: ColumnMappingStepProps) {
  return (
    <div className="grid gap-x-6 gap-y-4 md:grid-cols-2">
      {CANONICAL_FIELDS.map((field) => {
        const id = `map-${field.id}`;
        const missing = field.required && !mapping[field.id];
        return (
          <div key={field.id}>
            <label htmlFor={id} className="mb-1 flex items-center justify-between text-sm font-medium text-emphasis">
              <span>{field.label}{field.required && <span className="ml-0.5 text-danger" aria-label="required">*</span>}</span>
              {!field.required && <span className="text-xs font-normal text-muted">Optional</span>}
            </label>
            <Select id={id} value={mapping[field.id] ?? ""} aria-invalid={missing} onChange={(e) => onChange(field.id, e.target.value || undefined)} className={missing ? "border-danger" : undefined}>
              <option value="">Not mapped</option>
              {profile.columns.map((c) => (
                <option key={c.name} value={c.name}>{c.name} ({c.type})</option>
              ))}
            </Select>
            <p className="mt-1 text-xs text-muted">{field.description}</p>
          </div>
        );
      })}
    </div>
  );
}
