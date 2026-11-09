"use client";

import { Input } from "@/components/ui/input";
import type { ColumnFilterValue, TableColumn } from "@/types/table";

interface ColumnFilterProps<T> {
  column: TableColumn<T>;
  value: ColumnFilterValue;
  onChange: (value: ColumnFilterValue) => void;
}

/** Filter control for a single column: text contains, or min/max for numbers and dates. */
export function ColumnFilter<T>({ column, value, onChange }: ColumnFilterProps<T>) {
  const id = `filter-${column.key}`;
  const ranged = column.type === "number" || column.type === "date";
  const inputType = column.type === "date" ? "date" : "number";
  return (
    <div>
      <label htmlFor={ranged ? `${id}-min` : id} className="mb-1 block text-xs font-medium text-emphasis">{column.header}</label>
      {ranged ? (
        <div className="grid grid-cols-2 gap-2">
          <Input id={`${id}-min`} type={inputType} aria-label={`${column.header} minimum`} placeholder="Min" value={value.min ?? ""} onChange={(e) => onChange({ ...value, min: e.target.value })} className="h-9" />
          <Input id={`${id}-max`} type={inputType} aria-label={`${column.header} maximum`} placeholder="Max" value={value.max ?? ""} onChange={(e) => onChange({ ...value, max: e.target.value })} className="h-9" />
        </div>
      ) : (
        <Input id={id} placeholder="Contains…" value={value.text ?? ""} onChange={(e) => onChange({ ...value, text: e.target.value })} className="h-9" />
      )}
    </div>
  );
}
