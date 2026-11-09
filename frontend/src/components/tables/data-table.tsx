"use client";

import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown, ListFilter } from "lucide-react";
import { SearchInput } from "@/components/filters/search-input";
import { Button } from "@/components/ui/button";
import { Popover } from "@/components/ui/popover";
import { EmptyState } from "@/components/feedback/empty-state";
import { tableConfig } from "@/config/table";
import { useTableState } from "@/hooks/use-table-state";
import { toast } from "@/stores/toast.store";
import type { SortState, TableColumn } from "@/types/table";
import { toCsv } from "@/utils/csv";
import { downloadTextFile, slugify } from "@/utils/download";
import { cn } from "@/utils/cn";
import { ColumnFilter } from "./column-filter";
import { ColumnVisibilityMenu } from "./column-visibility-menu";
import { ExportMenu, type ExportFormat } from "./export-menu";
import { Pagination } from "./pagination";

interface DataTableProps<T> {
  data: readonly T[];
  columns: TableColumn<T>[];
  getRowId: (row: T, index: number) => string;
  /** Accessible table name, also used for export file names. */
  caption: string;
  onRowClick?: (row: T) => void;
  initialSort?: SortState;
  pageSize?: number;
  searchable?: boolean;
  exportable?: boolean;
  toolbar?: ReactNode;
  emptyMessage?: string;
  className?: string;
  serverPagination?: { page: number; pageCount: number; total: number; onPageChange: (page: number) => void; onCriteriaChange?: () => void };
}

/** Generic table: search, column filters, sorting, column visibility, pagination, row click and export. */
export function DataTable<T>({
  data,
  columns,
  getRowId,
  caption,
  onRowClick,
  initialSort,
  pageSize = tableConfig.defaultPageSize,
  searchable = true,
  exportable = true,
  toolbar,
  emptyMessage = "No rows match your search or filters.",
  className,
  serverPagination,
}: DataTableProps<T>) {
  const t = useTableState({ data, columns, pageSize, initialSort });
  const filterable = columns.filter((c) => c.filterable !== false);

  const handleExport = (format: ExportFormat) => {
    const cols = t.visibleColumns;
    const name = `${slugify(caption)}.${format}`;
    const rows = t.processed.slice(0, tableConfig.maxRowsInExport);
    if (format === "csv") {
      downloadTextFile(name, toCsv(cols.map((c) => c.header), rows.map((r) => cols.map((c) => c.accessor(r)))), "text/csv");
    } else {
      downloadTextFile(name, JSON.stringify(rows.map((r) => Object.fromEntries(cols.map((c) => [c.header, c.accessor(r)]))), null, 2), "application/json");
    }
    toast.success("Export ready", `${rows.length.toLocaleString()} rows saved as ${name}`);
  };

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex flex-wrap items-center gap-2">
        {searchable && <SearchInput value={t.search} onChange={(value) => { t.setSearch(value); serverPagination?.onCriteriaChange?.(); }} placeholder="Search all columns…" label={`Search ${caption}`} className="w-full sm:w-72" />}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {toolbar}
          <Popover
            align="end"
            panelClassName="w-80 max-h-96 overflow-y-auto p-4"
            trigger={({ open, toggle, panelId }) => (
              <Button variant="secondary" onClick={toggle} aria-expanded={open} aria-controls={panelId}>
                <ListFilter className="size-4" aria-hidden /> Filters
                {t.activeFilterCount > 0 && <span className="rounded-full bg-primary px-1.5 text-xs text-primary-foreground">{t.activeFilterCount}</span>}
              </Button>
            )}
          >
            <div className="space-y-3">
              {filterable.map((c) => (
                <ColumnFilter key={c.key} column={c} value={t.filters[c.key] ?? {}} onChange={(v) => { t.setFilter(c.key, v); serverPagination?.onCriteriaChange?.(); }} />
              ))}
              {t.activeFilterCount > 0 && (
                <Button size="sm" variant="ghost" onClick={() => { t.clearFilters(); serverPagination?.onCriteriaChange?.(); }} className="w-full">Clear all filters</Button>
              )}
            </div>
          </Popover>
          <ColumnVisibilityMenu columns={columns} hidden={t.hidden} onToggle={t.toggleColumn} />
          {exportable && <ExportMenu onExport={handleExport} disabled={t.total === 0} description={`${t.total.toLocaleString()} rows · visible columns`} />}
        </div>
      </div>

      <div className="scrollbar-thin overflow-x-auto rounded-lg border border-border bg-surface">
        <table className="w-full min-w-max border-collapse text-sm">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-surface-muted">
            <tr>
              {t.visibleColumns.map((c) => {
                const sorted = t.sort?.key === c.key ? t.sort.direction : null;
                const SortIcon = sorted === "asc" ? ArrowUp : sorted === "desc" ? ArrowDown : ChevronsUpDown;
                return (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={sorted ? (sorted === "asc" ? "ascending" : "descending") : undefined}
                    className={cn("whitespace-nowrap border-b border-border px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted", c.align === "right" || c.type === "number" ? "text-right" : "text-left")}
                  >
                    {c.sortable === false ? (
                      c.header
                    ) : (
                      <button type="button" onClick={() => { t.toggleSort(c.key); serverPagination?.onCriteriaChange?.(); }} className="inline-flex items-center gap-1 uppercase hover:text-foreground">
                        {c.header}
                        <SortIcon className={cn("size-3.5", !sorted && "opacity-50")} aria-hidden />
                      </button>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {t.pageRows.map((row, i) => (
              <tr
                key={getRowId(row, t.page * t.pageSize + i)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={onRowClick ? (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onRowClick(row)) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                className={cn("border-b border-border last:border-0", onRowClick && "cursor-pointer hover:bg-surface-accent focus-visible:bg-surface-accent")}
              >
                {t.visibleColumns.map((c) => (
                  <td key={c.key} className={cn("whitespace-nowrap px-4 py-2.5 text-foreground", (c.align === "right" || c.type === "number") && "tabular text-right")}>
                    {c.render ? c.render(row) : (c.accessor(row) ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {t.total === 0 && <EmptyState title="Nothing to show" description={emptyMessage} className="rounded-none border-0" />}
      </div>

      <Pagination page={serverPagination?.page ?? t.page} pageCount={serverPagination?.pageCount ?? t.pageCount} pageSize={t.pageSize} total={serverPagination?.total ?? t.total} onPageChange={serverPagination?.onPageChange ?? t.setPage} onPageSizeChange={serverPagination ? undefined : t.setPageSize} />
    </div>
  );
}
