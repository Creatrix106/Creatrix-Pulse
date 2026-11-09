import { FileSpreadsheet } from "lucide-react";
import { formatBytes } from "@/utils/format";

interface UploadProgressProps {
  fileName: string;
  fileSize: number;
  /** Real upload progress, 0-100. */
  percent: number;
}

export function UploadProgress({ fileName, fileSize, percent }: UploadProgressProps) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-md bg-accent-soft text-accent"><FileSpreadsheet className="size-5" aria-hidden /></span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-emphasis">{fileName}</p>
          <p className="text-xs text-muted">{formatBytes(fileSize)}</p>
        </div>
        <p className="tabular text-sm font-semibold text-emphasis">{percent}%</p>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface-accent" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-label="Upload progress">
        <div className="h-full rounded-full bg-accent transition-[width] duration-200" style={{ width: `${percent}%` }} />
      </div>
      <p className="mt-3 text-xs text-muted" aria-live="polite">{percent < 100 ? "Uploading your file…" : "Upload complete. Starting processing…"}</p>
    </div>
  );
}
