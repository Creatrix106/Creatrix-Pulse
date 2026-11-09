"use client";

import { useState } from "react";
import { CalendarRange } from "lucide-react";
import { Popover } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Input, FormField } from "@/components/ui/input";

interface DateRangePickerProps {
  from?: string;
  to?: string;
  min?: string;
  max?: string;
  onApply: (from: string, to: string) => void;
  /** Visible label for the trigger. */
  label?: string;
  active?: boolean;
}

export function DateRangePicker({ from, to, min, max, onApply, label = "Custom range", active }: DateRangePickerProps) {
  return (
    <Popover
      panelClassName="w-72 p-4"
      trigger={({ open, toggle, panelId }) => (
        <Button size="sm" variant={active ? "primary" : "secondary"} onClick={toggle} aria-expanded={open} aria-controls={panelId}>
          <CalendarRange className="size-4" aria-hidden /> {label}
        </Button>
      )}
    >
      {(close) => <RangeForm key={`${from}-${to}`} {...{ from, to, min, max, onApply, close }} />}
    </Popover>
  );
}

function RangeForm({ from, to, min, max, onApply, close }: Pick<DateRangePickerProps, "from" | "to" | "min" | "max" | "onApply"> & { close: () => void }) {
  const [start, setStart] = useState(from ?? min ?? "");
  const [end, setEnd] = useState(to ?? max ?? "");
  const invalid = !start || !end || start > end;

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (invalid) return;
        onApply(start, end);
        close();
      }}
    >
      <FormField label="From" htmlFor="range-from">
        <Input id="range-from" type="date" value={start} min={min} max={end || max} onChange={(e) => setStart(e.target.value)} />
      </FormField>
      <FormField label="To" htmlFor="range-to" error={start && end && start > end ? "End date must be after start date." : undefined}>
        <Input id="range-to" type="date" value={end} min={start || min} max={max} onChange={(e) => setEnd(e.target.value)} />
      </FormField>
      <Button type="submit" size="sm" className="w-full" disabled={invalid}>Apply range</Button>
    </form>
  );
}
