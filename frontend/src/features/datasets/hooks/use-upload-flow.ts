"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { FILE_ACCEPT, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB } from "@/config/files";
import { featureFlags } from "@/config/features";
import { useUploadDataset } from "@/hooks/use-datasets";
import { getErrorMessage } from "@/services/api-client";
import { toast } from "@/stores/toast.store";
import type { CanonicalField, ColumnMapping, DatasetProfile, ValidationIssue } from "@/types/dataset";
import { fileKindFromName, profileCsv, suggestMapping, validateUpload } from "@/utils/dataset-profile";

export type UploadStage = "select" | "reading" | "review" | "uploading";

/** All client-side state for the upload page. UI components stay presentational. */
export function useUploadFlow(replaceDatasetId?: string) {
  const router = useRouter();
  const [stage, setStage] = useState<UploadStage>("select");
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping>({});
  const [fileError, setFileError] = useState<string>();
  const [percent, setPercent] = useState(0);
  const upload = useUploadDataset(setPercent);

  const reset = useCallback(() => {
    setStage("select");
    setFile(null);
    setProfile(null);
    setMapping({});
    setFileError(undefined);
    setPercent(0);
    upload.reset();
  }, [upload]);

  const selectFile = useCallback(async (next: File) => {
    setFileError(undefined);
    const kind = fileKindFromName(next.name);
    if (!kind) {
      setFileError(`Unsupported file type. Please upload a ${FILE_ACCEPT.split(",").join(", ")} file.`);
      return;
    }
    if (next.size === 0) {
      setFileError("This file is empty.");
      return;
    }
    if (next.size > MAX_FILE_SIZE_BYTES) {
      setFileError(`This file is larger than ${MAX_FILE_SIZE_MB} MB.`);
      return;
    }
    setStage("reading");
    try {
      if (kind === "csv") {
        const parsed = profileCsv(await next.text());
        setProfile(parsed);
        setMapping(suggestMapping(parsed.headers));
      } else {
        // Excel is parsed by the backend – there is no browser-side preview.
        setProfile(null);
        setMapping({});
      }
      setFile(next);
      setStage("review");
    } catch {
      setFileError("We couldn’t read this file. Make sure it is a valid spreadsheet.");
      setStage("select");
    }
  }, []);

  const issues = useMemo<ValidationIssue[]>(() => {
    if (!file) return [];
    if (!profile) {
      return featureFlags.excelPreview
        ? []
        : [{ id: "excel-preview", severity: "warning", message: "Excel files are validated and mapped by the server after upload, so no preview is shown here." }];
    }
    return validateUpload(profile, mapping);
  }, [file, profile, mapping]);

  const hasErrors = issues.some((i) => i.severity === "error");

  const setMappingField = useCallback((field: CanonicalField, column: string | undefined) => {
    setMapping((prev) => {
      const next = { ...prev };
      if (column) next[field] = column;
      else delete next[field];
      return next;
    });
  }, []);

  const submit = useCallback(() => {
    if (!file || hasErrors) return;
    setStage("uploading");
    setPercent(0);
    upload.mutate(
      { file, mapping, profile, replaceDatasetId },
      {
        onSuccess: ({ datasetId }) => router.push(`/processing/${datasetId}`),
        onError: (error) => {
          toast.error("Upload failed", getErrorMessage(error));
          setStage("review");
        },
      },
    );
  }, [file, hasErrors, mapping, profile, replaceDatasetId, router, upload]);

  return {
    stage,
    file,
    profile,
    mapping,
    issues,
    hasErrors,
    fileError,
    percent,
    uploadError: upload.isError ? getErrorMessage(upload.error) : undefined,
    selectFile,
    setMappingField,
    submit,
    reset,
  };
}
