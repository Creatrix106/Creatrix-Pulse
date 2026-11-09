"use client";

import { FileSpreadsheet, RefreshCw, X } from "lucide-react";
import { InlineError } from "@/components/feedback/inline-error";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { ColumnMappingStep } from "@/components/upload/column-mapping-step";
import { DataQualitySummary } from "@/components/upload/data-quality-summary";
import { DatasetPreviewTable } from "@/components/upload/dataset-preview-table";
import { FileUploadDropzone } from "@/components/upload/file-upload-dropzone";
import { UploadProgress } from "@/components/upload/upload-progress";
import { ValidationErrorList } from "@/components/upload/validation-error-list";
import { CANONICAL_FIELDS, MAX_FILE_SIZE_MB } from "@/config/files";
import { useDataset } from "@/hooks/use-datasets";
import { formatBytes } from "@/utils/format";
import { useUploadFlow } from "./hooks/use-upload-flow";

const instructions = [
  "Use one row per order or sale, with a header row in the first line.",
  `Required columns: ${CANONICAL_FIELDS.filter((f) => f.required).map((f) => f.label.toLowerCase()).join(", ")}.`,
  "Optional columns (category, region, customer, cost) unlock extra analytics.",
  `CSV and Excel files up to ${MAX_FILE_SIZE_MB} MB are supported.`,
];

export function UploadView({ replaceDatasetId }: { replaceDatasetId?: string }) {
  const flow = useUploadFlow(replaceDatasetId);
  const replacing = useDataset(replaceDatasetId ?? "");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-emphasis">{replaceDatasetId ? "Replace dataset" : "Upload your dataset"}</h1>
        <p className="mt-2 text-muted">Add a CSV or Excel file and Creatrix Pulse will turn it into an interactive analytics dashboard.</p>
      </div>

      {replaceDatasetId && (
        <p className="flex items-start gap-2 rounded-md bg-warning-soft px-3 py-2.5 text-sm text-warning" role="status">
          <RefreshCw className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>You’re replacing <strong>{replacing.data?.name ?? "an existing dataset"}</strong>. It will be removed once the new file is uploaded.</span>
        </p>
      )}

      {(flow.stage === "select" || flow.stage === "reading") && (
        <>
          <FileUploadDropzone onFile={flow.selectFile} loading={flow.stage === "reading"} error={flow.fileError} />
          <Card className="p-5">
            <CardHeader title="Before you upload" />
            <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-muted">
              {instructions.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          </Card>
        </>
      )}

      {flow.stage === "review" && flow.file && (
        <>
          <Card className="flex flex-wrap items-center gap-3 p-4">
            <span className="grid size-10 place-items-center rounded-md bg-accent-soft text-accent"><FileSpreadsheet className="size-5" aria-hidden /></span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-emphasis">{flow.file.name}</p>
              <p className="text-xs text-muted">{formatBytes(flow.file.size)}{flow.profile ? ` · ${flow.profile.rowCount.toLocaleString()} rows · ${flow.profile.columns.length} columns` : " · Excel workbook"}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={flow.reset}><X className="size-4" aria-hidden /> Choose another file</Button>
          </Card>

          <Card className="space-y-4 p-5">
            <CardHeader title="Validation" description="Checks run in your browser before upload" />
            <ValidationErrorList issues={flow.issues} />
          </Card>

          {flow.profile && (
            <>
              <Card className="space-y-4 p-5">
                <CardHeader title="Data quality" description="A quick health check of your file" />
                <DataQualitySummary profile={flow.profile} />
              </Card>
              <Card className="space-y-4 p-5">
                <CardHeader title="Map your columns" description="We matched what we could. Adjust anything that looks wrong." />
                <ColumnMappingStep profile={flow.profile} mapping={flow.mapping} onChange={flow.setMappingField} />
              </Card>
              <Card className="space-y-4 p-5">
                <CardHeader title="Preview" description={`First ${flow.profile.previewRows.length} rows`} />
                <DatasetPreviewTable profile={flow.profile} />
              </Card>
            </>
          )}

          <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center justify-end gap-3 border-t border-border bg-background/95 px-4 py-4 backdrop-blur sm:mx-0 sm:rounded-lg sm:border">
            {flow.hasErrors && <p className="mr-auto text-sm text-danger">Fix the issues above to continue.</p>}
            <Button variant="secondary" onClick={flow.reset}>Cancel</Button>
            <Button onClick={flow.submit} disabled={flow.hasErrors}>Upload &amp; analyze</Button>
          </div>
        </>
      )}

      {flow.stage === "uploading" && flow.file && (
        <>
          <UploadProgress fileName={flow.file.name} fileSize={flow.file.size} percent={flow.percent} />
          <InlineError message={flow.uploadError} />
        </>
      )}
    </div>
  );
}
