import { CANONICAL_FIELDS, PREVIEW_ROW_COUNT } from "@/config/files";
import type {
  ColumnMapping,
  ColumnType,
  DatasetProfile,
  ProfiledColumn,
  ValidationIssue,
} from "@/types/dataset";
import { parseCsv } from "./csv";

const DATE_RE = /^\d{4}-\d{1,2}-\d{1,2}([T ].*)?$|^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$/;
const NUMBER_RE = /^[-+]?[₹$€£]?\s?[\d,]*\.?\d+$/;

export function normaliseHeader(header: string): string {
  return header.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function inferType(values: string[]): ColumnType {
  const filled = values.filter((v) => v.trim() !== "");
  if (filled.length === 0) return "string";
  const share = (test: (v: string) => boolean) => filled.filter(test).length / filled.length;
  if (share((v) => DATE_RE.test(v.trim())) > 0.9) return "date";
  if (share((v) => NUMBER_RE.test(v.trim())) > 0.9) return "number";
  if (share((v) => /^(true|false|yes|no)$/i.test(v.trim())) > 0.9) return "boolean";
  return "string";
}

/** Builds a profile (types, missing values, duplicates, preview) from CSV text. */
export function profileCsv(text: string): DatasetProfile {
  const [headerRow, ...body] = parseCsv(text);
  const headers = (headerRow ?? []).map((h, i) => h.trim() || `Column ${i + 1}`);

  const columns: ProfiledColumn[] = headers.map((name, index) => {
    const values = body.map((r) => r[index] ?? "");
    const missing = values.filter((v) => v.trim() === "").length;
    return {
      name,
      type: inferType(values),
      missing,
      unique: new Set(values.filter((v) => v.trim() !== "")).size,
      sample: values.filter((v) => v.trim() !== "").slice(0, 3),
    };
  });

  const missingCells = columns.reduce((sum, c) => sum + c.missing, 0);
  const totalCells = headers.length * body.length;
  const seen = new Set<string>();
  let duplicateRows = 0;
  for (const row of body) {
    const key = row.join("\u0001");
    if (seen.has(key)) duplicateRows++;
    else seen.add(key);
  }

  return {
    fileKind: "csv",
    headers,
    rowCount: body.length,
    columns,
    missingCells,
    missingPercent: totalCells === 0 ? 0 : (missingCells / totalCells) * 100,
    duplicateRows,
    previewRows: body.slice(0, PREVIEW_ROW_COUNT).map((r) => headers.map((_, i) => r[i] ?? "")),
  };
}

/** Suggests a mapping from column headers to canonical business fields. */
export function suggestMapping(headers: string[]): ColumnMapping {
  const mapping: ColumnMapping = {};
  const used = new Set<string>();
  for (const field of CANONICAL_FIELDS) {
    const match = headers.find((h) => !used.has(h) && field.aliases.includes(normaliseHeader(h)));
    if (match) {
      mapping[field.id] = match;
      used.add(match);
    }
  }
  return mapping;
}

/** Client-side validation shown before upload. The backend remains the source of truth. */
export function validateUpload(profile: DatasetProfile | null, mapping: ColumnMapping): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  for (const field of CANONICAL_FIELDS.filter((f) => f.required)) {
    if (!mapping[field.id]) {
      issues.push({
        id: `missing-${field.id}`,
        severity: "error",
        message: `Map a column to "${field.label}" – it is required to generate analytics.`,
      });
    }
  }
  if (!profile) return issues;

  if (profile.rowCount === 0) {
    issues.push({ id: "empty", severity: "error", message: "The file has no data rows." });
  }
  const typeExpectation: Partial<Record<keyof ColumnMapping, ColumnType>> = {
    date: "date",
    revenue: "number",
    quantity: "number",
    cost: "number",
  };
  for (const [field, expected] of Object.entries(typeExpectation)) {
    const column = mapping[field as keyof ColumnMapping];
    const profiled = profile.columns.find((c) => c.name === column);
    if (profiled && profiled.type !== expected) {
      issues.push({
        id: `type-${field}`,
        severity: "error",
        column: profiled.name,
        message: `"${profiled.name}" looks like ${profiled.type} data but is mapped to a ${expected} field.`,
      });
    }
  }
  for (const col of profile.columns) {
    if (profile.rowCount > 0 && col.missing / profile.rowCount > 0.2) {
      issues.push({
        id: `missing-${col.name}`,
        severity: "warning",
        column: col.name,
        message: `"${col.name}" is empty in ${col.missing.toLocaleString()} rows (${Math.round((col.missing / profile.rowCount) * 100)}%).`,
      });
    }
  }
  if (profile.duplicateRows > 0) {
    issues.push({
      id: "duplicates",
      severity: "warning",
      message: `${profile.duplicateRows.toLocaleString()} duplicate rows detected. They may inflate totals.`,
    });
  }
  return issues;
}

export function fileKindFromName(name: string): "csv" | "excel" | null {
  const lower = name.toLowerCase();
  if (lower.endsWith(".csv")) return "csv";
  if (lower.endsWith(".xlsx") || lower.endsWith(".xls")) return "excel";
  return null;
}
