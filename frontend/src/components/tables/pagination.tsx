"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { tableConfig } from "@/config/table";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";

interface PaginationProps {
  page: number; // zero-based
  pageCount: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
}

export function Pagination({ page, pageCount, pageSize, total, onPageChange, onPageSizeChange }: PaginationProps) {
  const from = total === 0 ? 0 : page * pageSize + 1;
  const to = Math.min(total, (page + 1) * pageSize);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
      <p aria-live="polite">
        Showing <span className="tabular font-medium text-foreground">{from.toLocaleString()}–{to.toLocaleString()}</span> of{" "}
        <span className="tabular font-medium text-foreground">{total.toLocaleString()}</span>
      </p>
      <div className="flex items-center gap-2">
        {onPageSizeChange && (
          <Select size="sm" aria-label="Rows per page" value={pageSize} onChange={(e) => onPageSizeChange(Number(e.target.value))} wrapperClassName="w-24">
            {tableConfig.pageSizeOptions.map((s) => (
              <option key={s} value={s}>{s} / page</option>
            ))}
          </Select>
        )}
        <Button size="sm" variant="secondary" onClick={() => onPageChange(page - 1)} disabled={page === 0} aria-label="Previous page">
          <ChevronLeft className="size-4" aria-hidden />
        </Button>
        <span className="tabular min-w-20 text-center">Page {page + 1} of {pageCount}</span>
        <Button size="sm" variant="secondary" onClick={() => onPageChange(page + 1)} disabled={page >= pageCount - 1} aria-label="Next page">
          <ChevronRight className="size-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
