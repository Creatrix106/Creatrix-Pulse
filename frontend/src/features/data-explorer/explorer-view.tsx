"use client";

import { useMemo, useState } from "react";
import { QueryBoundary } from "@/components/feedback/query-boundary";
import { TableSkeleton } from "@/components/feedback/skeletons";
import { Card } from "@/components/ui/card";
import { DataTable } from "@/components/tables/data-table";
import { RowDetailsDrawer } from "@/components/tables/row-details-drawer";
import { useExplorerQuery } from "@/hooks/use-analytics";
import { useFormatters } from "@/hooks/use-formatters";
import { usePreferencesStore } from "@/stores/preferences.store";
import { useDatasetId } from "@/hooks/use-dataset-id";
import { useAuthStore } from "@/stores/auth.store";
import type { ExplorerData, ExplorerRow } from "@/types/analytics";
import type { TableColumn } from "@/types/table";

function ExplorerContent({ data, page, pageSize, onPageChange }: { data: ExplorerData; page: number; pageSize: number; onPageChange: (page: number) => void }) {
  const f = useFormatters();
  const [selected, setSelected] = useState<ExplorerRow | null>(null);

  const columns = useMemo<TableColumn<ExplorerRow>[]>(
    () =>
      data.columns.map((c) => ({
        key: c.key,
        header: c.label,
        type: c.type,
        accessor: (row) => row[c.key] ?? null,
        render:
          c.format === "currency"
            ? (row) => (typeof row[c.key] === "number" ? f.currency(row[c.key] as number) : "—")
            : c.type === "date"
              ? (row) => (row[c.key] ? f.date(String(row[c.key]), "long") : "—")
              : undefined,
      })),
    [data.columns, f],
  );

  const fields = selected
    ? data.columns.map((c) => {
        const raw = selected[c.key];
        const value = raw === null || raw === undefined ? "" : c.format === "currency" && typeof raw === "number" ? f.currency(raw) : c.type === "date" ? f.date(String(raw), "long") : String(raw);
        return { label: c.label, value };
      })
    : [];

  return (
    <Card className="p-4 sm:p-5">
      <DataTable
        data={data.rows}
        columns={columns}
        getRowId={(row, i) => String(row.orderId ?? i)}
        caption="Dataset records"
        pageSize={pageSize}
        serverPagination={{ page, pageCount: Math.max(1, Math.ceil(data.total / pageSize)), total: data.total, onPageChange, onCriteriaChange: () => onPageChange(0) }}
        onRowClick={setSelected}
        initialSort={{ key: "date", direction: "desc" }}
      />
      <RowDetailsDrawer open={selected !== null} onClose={() => setSelected(null)} title={selected ? `Record ${String(selected.orderId ?? "")}` : "Record"} description="All fields for the selected row, including hidden columns." fields={fields} />
    </Card>
  );
}

function ExplorerPage({ pageSize }: { pageSize: number }) {
  const [page, setPage] = useState(0);
  const query = useExplorerQuery(page, pageSize);
  return (
    <QueryBoundary query={query} loading={<TableSkeleton rows={10} columns={7} />}>
      {(data) => <ExplorerContent data={data} page={page} pageSize={pageSize} onPageChange={setPage} />}
    </QueryBoundary>
  );
}

export function ExplorerView() {
  const datasetId = useDatasetId();
  const userId = useAuthStore((s) => s.user?.id ?? null);
  const pageSize = usePreferencesStore((s) => s.pageSize);
  return <ExplorerPage key={`${userId ?? "signed-out"}:${datasetId}:${pageSize}`} pageSize={pageSize} />;
}
