"use client";

import { useMemo, useState } from "react";
import type { ColumnFilterValue, SortState, TableColumn } from "@/types/table";

interface Options<T> {
  data: readonly T[];
  columns: TableColumn<T>[];
  pageSize: number;
  initialSort?: SortState;
}

/** Search, column filters, sorting, column visibility and pagination – all table logic, no UI. */
export function useTableState<T>({ data, columns, pageSize: initialPageSize, initialSort }: Options<T>) {
  const [search, setSearchRaw] = useState("");
  const [filters, setFilters] = useState<Record<string, ColumnFilterValue>>({});
  const [sort, setSort] = useState<SortState | null>(initialSort ?? null);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSizeRaw] = useState(initialPageSize);
  const [hidden, setHidden] = useState<Set<string>>(() => new Set(columns.filter((c) => c.defaultHidden).map((c) => c.key)));

  const processed = useMemo(() => {
    const term = search.trim().toLowerCase();
    const activeFilters = Object.entries(filters).filter(([, v]) => v.text || v.min || v.max);
    let rows = data.filter((row) => {
      if (term && !columns.some((c) => String(c.accessor(row) ?? "").toLowerCase().includes(term))) return false;
      return activeFilters.every(([key, f]) => {
        const col = columns.find((c) => c.key === key);
        if (!col) return true;
        const value = col.accessor(row);
        if (f.text && !String(value ?? "").toLowerCase().includes(f.text.toLowerCase())) return false;
        if (f.min || f.max) {
          if (col.type === "date") {
            const v = String(value ?? "");
            return (!f.min || v >= f.min) && (!f.max || v <= f.max);
          }
          const n = Number(value);
          if (!Number.isFinite(n)) return false;
          if (f.min && n < Number(f.min)) return false;
          if (f.max && n > Number(f.max)) return false;
        }
        return true;
      });
    });
    if (sort) {
      const col = columns.find((c) => c.key === sort.key);
      if (col) {
        const dir = sort.direction === "asc" ? 1 : -1;
        rows = [...rows].sort((a, b) => {
          const va = col.accessor(a);
          const vb = col.accessor(b);
          if (va === null || va === undefined) return 1;
          if (vb === null || vb === undefined) return -1;
          if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
          return String(va).localeCompare(String(vb)) * dir;
        });
      }
    }
    return rows;
  }, [data, columns, search, filters, sort]);

  const pageCount = Math.max(1, Math.ceil(processed.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = useMemo(() => processed.slice(safePage * pageSize, (safePage + 1) * pageSize), [processed, safePage, pageSize]);
  const visibleColumns = useMemo(() => columns.filter((c) => !hidden.has(c.key)), [columns, hidden]);
  const activeFilterCount = Object.values(filters).filter((v) => v.text || v.min || v.max).length;

  return {
    search,
    setSearch: (value: string) => {
      setSearchRaw(value);
      setPage(0);
    },
    filters,
    setFilter: (key: string, value: ColumnFilterValue) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
      setPage(0);
    },
    clearFilters: () => {
      setFilters({});
      setPage(0);
    },
    activeFilterCount,
    sort,
    toggleSort: (key: string) =>
      setSort((prev) => (prev?.key !== key ? { key, direction: "asc" } : prev.direction === "asc" ? { key, direction: "desc" } : null)),
    page: safePage,
    setPage,
    pageSize,
    setPageSize: (size: number) => {
      setPageSizeRaw(size);
      setPage(0);
    },
    pageCount,
    total: processed.length,
    processed,
    pageRows,
    visibleColumns,
    hidden,
    toggleColumn: (key: string) =>
      setHidden((prev) => {
        const next = new Set(prev);
        if (next.has(key)) next.delete(key);
        else next.add(key);
        return next;
      }),
  };
}
