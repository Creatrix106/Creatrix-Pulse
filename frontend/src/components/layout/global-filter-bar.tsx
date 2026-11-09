"use client";

import { usePathname } from "next/navigation";
import { ActiveFilterChips, type FilterChip } from "@/components/filters/active-filter-chips";
import { DateRangePicker } from "@/components/filters/date-range-picker";
import { FilterPopover } from "@/components/filters/filter-popover";
import { ComparisonSelector, DatePresetSelector } from "@/components/filters/option-selectors";
import { DATE_PRESETS } from "@/config/filters";
import { findPageByPathname } from "@/config/navigation";
import { useDataset } from "@/hooks/use-datasets";
import { useFormatters } from "@/hooks/use-formatters";
import { useFiltersStore } from "@/stores/filters.store";

/** Global date / comparison / category / region filters. Visibility is driven by `showGlobalFilters` in the nav config. */
export function GlobalFilterBar({ datasetId }: { datasetId: string }) {
  const pathname = usePathname();
  const page = findPageByPathname(pathname, datasetId);
  const { data: dataset } = useDataset(datasetId);
  const f = useFormatters();
  const filters = useFiltersStore();

  if (!page?.showGlobalFilters) return null;

  const chips: FilterChip[] = [];
  if (filters.datePreset !== "all") {
    chips.push({
      id: "date",
      label: filters.datePreset === "custom" && filters.dateFrom && filters.dateTo
        ? `${f.date(filters.dateFrom, "long")} – ${f.date(filters.dateTo, "long")}`
        : DATE_PRESETS.find((p) => p.value === filters.datePreset)?.label ?? filters.datePreset,
      onRemove: () => filters.setDatePreset("all"),
    });
  }
  if (filters.comparison !== "none") chips.push({ id: "cmp", label: "Compared with previous period", onRemove: () => filters.setComparison("none") });
  filters.categories.forEach((c) => chips.push({ id: `cat-${c}`, label: c, onRemove: () => filters.setCategories(filters.categories.filter((x) => x !== c)) }));
  filters.regions.forEach((r) => chips.push({ id: `reg-${r}`, label: `Region: ${r}`, onRemove: () => filters.setRegions(filters.regions.filter((x) => x !== r)) }));

  const range = dataset?.dateRange;
  return (
    <div className="border-b border-border bg-surface-muted px-[var(--space-page-x)] py-3">
      <div className="mx-auto flex max-w-[var(--page-max-width)] flex-wrap items-center gap-2">
        <DatePresetSelector value={filters.datePreset} onChange={filters.setDatePreset} className="w-40" />
        <DateRangePicker
          from={filters.dateFrom}
          to={filters.dateTo}
          min={range?.from}
          max={range?.to}
          active={filters.datePreset === "custom"}
          onApply={filters.setCustomRange}
        />
        <ComparisonSelector value={filters.comparison} onChange={filters.setComparison} className="w-44" />
        <FilterPopover
          groups={[
            { id: "categories", label: "Category", options: dataset?.filterOptions.categories ?? [], selected: filters.categories, onChange: filters.setCategories },
            { id: "regions", label: "Region", options: dataset?.filterOptions.regions ?? [], selected: filters.regions, onChange: filters.setRegions },
          ]}
        />
        {range && <span className="ml-auto hidden text-xs text-muted xl:inline">Data from {f.date(range.from, "long")} to {f.date(range.to, "long")}</span>}
      </div>
      {chips.length > 0 && (
        <div className="mx-auto mt-3 max-w-[var(--page-max-width)]">
          <ActiveFilterChips chips={chips} onClearAll={() => filters.reset("all")} />
        </div>
      )}
    </div>
  );
}
