import type { ReactNode } from "react";

export interface TableColumn<T> {
  key: string;
  header: string;
  /** Raw value used for search, sort, filter and export. */
  accessor: (row: T) => string | number | null;
  /** Custom cell renderer. Defaults to the accessor value. */
  render?: (row: T) => ReactNode;
  type?: "string" | "number" | "date";
  align?: "left" | "right";
  sortable?: boolean;
  filterable?: boolean;
  defaultHidden?: boolean;
}

export type SortDirection = "asc" | "desc";
export interface SortState {
  key: string;
  direction: SortDirection;
}

export interface ColumnFilterValue {
  text?: string;
  min?: string;
  max?: string;
}
