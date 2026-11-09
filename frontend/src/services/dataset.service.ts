import type { Dataset, ProcessingStatus, UploadRequest, UploadResult } from "@/types/dataset";
import { ApiError, apiClient } from "./api-client";

/**
 * BACKEND INTEGRATION POINT – datasets
 *   GET    /datasets                    -> Dataset[]
 *   GET    /datasets/:id                -> Dataset
 *   DELETE /datasets/:id                -> 204
 *   POST   /datasets  (multipart: file, mapping(JSON), replaceDatasetId?)  -> UploadResult
 *   GET    /datasets/:id/processing     -> ProcessingStatus (poll until status is "ready" | "failed")
 */
export interface DatasetService {
  list(): Promise<Dataset[]>;
  get(id: string): Promise<Dataset>;
  remove(id: string): Promise<void>;
  upload(request: UploadRequest, onProgress?: (percent: number) => void): Promise<UploadResult>;
  getProcessingStatus(id: string): Promise<ProcessingStatus>;
}

const httpDatasetService: DatasetService = {
  list: () => apiClient.get<Dataset[]>("/datasets"),
  get: (id) => apiClient.get<Dataset>(`/datasets/${encodeURIComponent(id)}`),
  remove: (id) => apiClient.delete(`/datasets/${encodeURIComponent(id)}`),
  upload: async ({ file, mapping, replaceDatasetId }, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    form.append("mapping", JSON.stringify(mapping));
    if (replaceDatasetId) form.append("replaceDatasetId", replaceDatasetId);
    const result = await apiClient.upload<UploadResult>("/datasets", form, { onProgress });
    if (!result || typeof result.datasetId !== "string" || result.datasetId.length === 0) {
      throw new ApiError(200, { code: "invalid_response", message: "The server did not return a dataset ID." });
    }
    return result;
  },
  getProcessingStatus: (id) => apiClient.get<ProcessingStatus>(`/datasets/${encodeURIComponent(id)}/processing`),
};

export const datasetService: DatasetService = httpDatasetService;
