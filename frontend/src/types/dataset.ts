export type DatasetStatus = "uploading" | "validating" | "processing" | "generating" | "ready" | "failed";

/** Business fields the analytics engine understands. Uploaded columns are mapped onto these. */
export type CanonicalField =
  | "date"
  | "orderId"
  | "product"
  | "category"
  | "region"
  | "customer"
  | "quantity"
  | "revenue"
  | "cost";

export type ColumnType = "string" | "number" | "date" | "boolean";
export type ColumnMapping = Partial<Record<CanonicalField, string>>;

export interface DatasetCapabilities {
  customers: boolean;
  cost: boolean;
  regions: boolean;
}

export interface DatasetColumn {
  name: string;
  type: ColumnType;
  mappedTo?: CanonicalField;
}

export interface Dataset {
  id: string;
  name: string;
  fileName: string;
  fileSize: number;
  rowCount: number;
  columnCount: number;
  status: DatasetStatus;
  uploadedAt: string;
  dateRange: { from: string; to: string } | null;
  capabilities: DatasetCapabilities;
  columns: DatasetColumn[];
  /** Values available to the global category / region filters. */
  filterOptions: { categories: string[]; regions: string[] };
  errorMessage?: string;
}

export type ProcessingStageId = "upload" | "validate" | "process" | "analytics" | "prepare";
export type ProcessingStageStatus = "pending" | "active" | "complete" | "failed";

export interface ProcessingStage {
  id: ProcessingStageId;
  label: string;
  status: ProcessingStageStatus;
}

export interface ProcessingStatus {
  datasetId: string;
  status: DatasetStatus;
  stages: ProcessingStage[];
  /** 0-100 when the backend reports real progress, otherwise null. The UI never invents a value. */
  progress: number | null;
  message?: string;
}

export interface ProfiledColumn {
  name: string;
  type: ColumnType;
  missing: number;
  unique: number;
  sample: string[];
}

export interface DatasetProfile {
  fileKind: "csv" | "excel";
  headers: string[];
  rowCount: number;
  columns: ProfiledColumn[];
  missingCells: number;
  missingPercent: number;
  duplicateRows: number;
  previewRows: string[][];
}

export interface ValidationIssue {
  id: string;
  severity: "error" | "warning";
  message: string;
  column?: string;
}

export interface UploadRequest {
  file: File;
  mapping: ColumnMapping;
  profile: DatasetProfile | null;
  replaceDatasetId?: string;
}

export interface UploadResult {
  datasetId: string;
}
