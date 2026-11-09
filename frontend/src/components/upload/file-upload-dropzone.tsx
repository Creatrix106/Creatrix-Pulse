"use client";

import { useState, type DragEvent } from "react";
import { FileUp, Loader2 } from "lucide-react";
import { FILE_ACCEPT, MAX_FILE_SIZE_MB, SUPPORTED_FILE_FORMATS } from "@/config/files";
import { cn } from "@/utils/cn";

interface FileUploadDropzoneProps {
  onFile: (file: File) => void;
  loading?: boolean;
  disabled?: boolean;
  error?: string;
}

/** Drag-and-drop target. A real <input type="file"> inside a label keeps it fully keyboard accessible. */
export function FileUploadDropzone({ onFile, loading, disabled, error }: FileUploadDropzoneProps) {
  const [dragging, setDragging] = useState(false);

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragging(false);
    if (disabled || loading) return;
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  };

  return (
    <div>
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-14 text-center transition-colors focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ring",
          dragging ? "border-accent bg-surface-accent" : "border-border-strong bg-surface hover:bg-surface-muted",
          error && "border-danger",
          (disabled || loading) && "pointer-events-none opacity-70",
        )}
      >
        <input
          type="file"
          accept={FILE_ACCEPT}
          className="sr-only"
          disabled={disabled || loading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = "";
          }}
        />
        <span className="mb-4 grid size-14 place-items-center rounded-full bg-accent-soft text-accent">
          {loading ? <Loader2 className="size-7 animate-spin" aria-hidden /> : <FileUp className="size-7" aria-hidden />}
        </span>
        <span className="text-base font-semibold text-emphasis">{loading ? "Reading your file…" : dragging ? "Drop to upload" : "Drag & drop your dataset here"}</span>
        <span className="mt-1 text-sm text-muted">or <span className="font-semibold text-accent underline underline-offset-2">browse files</span></span>
        <span className="mt-4 text-xs text-muted">
          {SUPPORTED_FILE_FORMATS.map((f) => f.extension).join(", ")} · up to {MAX_FILE_SIZE_MB} MB
        </span>
      </label>
      {error && <p role="alert" className="mt-2 text-sm font-medium text-danger">{error}</p>}
    </div>
  );
}
