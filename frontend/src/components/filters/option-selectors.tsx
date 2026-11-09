"use client";

import { COMPARISON_OPTIONS, DATE_PRESETS, GROUP_BY_OPTIONS, METRIC_OPTIONS } from "@/config/filters";
import type { Dataset } from "@/types/dataset";
import type { ComparisonMode, DatePreset, GroupBy, MetricKey } from "@/types/filters";
import { Select } from "@/components/ui/select";

interface BaseProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  className?: string;
  label?: string;
}

export function DatePresetSelector({ value, onChange, className, label = "Date range" }: BaseProps<DatePreset>) {
  return (
    <Select size="sm" aria-label={label} value={value} onChange={(e) => onChange(e.target.value as DatePreset)} wrapperClassName={className}>
      {DATE_PRESETS.map((p) => (
        <option key={p.value} value={p.value}>{p.label}</option>
      ))}
    </Select>
  );
}

export function ComparisonSelector({ value, onChange, className, label = "Compare to" }: BaseProps<ComparisonMode>) {
  return (
    <Select size="sm" aria-label={label} value={value} onChange={(e) => onChange(e.target.value as ComparisonMode)} wrapperClassName={className}>
      {COMPARISON_OPTIONS.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </Select>
  );
}

export function GroupBySelector({ value, onChange, className, label = "Group by" }: BaseProps<GroupBy>) {
  return (
    <Select size="sm" aria-label={label} value={value} onChange={(e) => onChange(e.target.value as GroupBy)} wrapperClassName={className}>
      {GROUP_BY_OPTIONS.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </Select>
  );
}

interface MetricSelectorProps extends BaseProps<MetricKey> {
  /** Restrict to these metrics (defaults to all metrics the dataset supports). */
  metrics?: MetricKey[];
  hasCost?: boolean;
}

export function MetricSelector({ value, onChange, className, label = "Metric", metrics, hasCost = true }: MetricSelectorProps) {
  const options = METRIC_OPTIONS.filter((m) => (metrics ? metrics.includes(m.value) : true) && (hasCost || !m.requiresCost));
  return (
    <Select size="sm" aria-label={label} value={value} onChange={(e) => onChange(e.target.value as MetricKey)} wrapperClassName={className}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </Select>
  );
}

interface DatasetSelectorProps extends BaseProps<string> {
  datasets: Dataset[];
}

export function DatasetSelector({ datasets, value, onChange, className, label = "Active dataset" }: DatasetSelectorProps) {
  return (
    <Select size="sm" aria-label={label} value={value} onChange={(e) => onChange(e.target.value)} wrapperClassName={className}>
      {!datasets.some((d) => d.id === value) && <option value={value}>{value}</option>}
      {datasets.map((d) => (
        <option key={d.id} value={d.id} disabled={d.status !== "ready" && d.id !== value}>
          {d.name}{d.status === "ready" ? "" : ` (${d.status})`}
        </option>
      ))}
    </Select>
  );
}
