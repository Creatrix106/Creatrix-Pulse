import { env } from "@/config/env";
import type { ApiErrorBody } from "@/types/api";
import { useAuthStore } from "@/stores/auth.store";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function getErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

type QueryValue = string | number | boolean | undefined | null | readonly string[];

export interface RequestOptions {
  query?: Record<string, QueryValue>;
  body?: unknown;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
    else params.append(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

function notifyUnauthorized(): void {
  if (typeof window === "undefined") return;
  useAuthStore.getState().setUser(null);
  window.dispatchEvent(new Event("creatrix:unauthorized"));
}

async function readErrorBody(response: Response): Promise<Partial<ApiErrorBody>> {
  const text = await response.text().catch(() => "");
  if (!text) return {};
  try {
    return JSON.parse(text) as Partial<ApiErrorBody>;
  } catch {
    return { message: text };
  }
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      credentials: "include", // session cookie issued by the backend
      signal: options.signal,
      headers: options.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(0, { code: "network_error", message: "Unable to reach the server. Check your connection." });
  }

  if (!response.ok) {
    const body = await readErrorBody(response);
    if (response.status === 401) notifyUnauthorized();
    throw new ApiError(response.status, {
      code: body.code ?? "http_error",
      message: body.message ?? `Request failed with status ${response.status}`,
      details: body.details,
    });
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(response.status, { code: "invalid_response", message: "The server returned an invalid JSON response." });
  }
}

/** Multipart upload with real progress events (fetch does not expose upload progress). */
function upload<T>(
  path: string,
  formData: FormData,
  opts: { onProgress?: (percent: number) => void; signal?: AbortSignal } = {},
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    if (opts.signal?.aborted) {
      reject(new DOMException("Upload cancelled", "AbortError"));
      return;
    }
    const xhr = new XMLHttpRequest();
    xhr.open("POST", buildUrl(path));
    xhr.withCredentials = true;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) opts.onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onload = () => {
      let parsed: unknown = null;
      let validJson = false;
      try {
        parsed = JSON.parse(xhr.responseText);
        validJson = true;
      } catch {
        /* non-JSON body */
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        if (!validJson || parsed === null) {
          reject(new ApiError(xhr.status, { code: "invalid_response", message: "The server returned an invalid upload response." }));
          return;
        }
        resolve(parsed as T);
      }
      else {
        const body = parsed as Partial<ApiErrorBody> | null;
        if (xhr.status === 401) notifyUnauthorized();
        reject(new ApiError(xhr.status, {
          code: body?.code ?? "upload_failed",
          message: body?.message ?? "Upload failed.",
          details: body?.details,
        }));
      }
    };
    xhr.onerror = () => reject(new ApiError(0, { code: "network_error", message: "Upload failed. Check your connection." }));
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    const abort = () => xhr.abort();
    opts.signal?.addEventListener("abort", abort, { once: true });
    xhr.onloadend = () => opts.signal?.removeEventListener("abort", abort);
    xhr.send(formData);
  });
}

export const apiClient = {
  resolveUrl: (path: string) => {
    if (/^https?:\/\//i.test(path)) return path;
    const baseUrl = new URL(`${env.apiBaseUrl.replace(/\/$/, "")}/`, window.location.origin);
    return new URL(path, baseUrl).toString();
  },
  get: <T>(path: string, options?: RequestOptions) => request<T>("GET", path, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>("POST", path, { ...options, body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>("PUT", path, { ...options, body }),
  delete: <T = void>(path: string, options?: RequestOptions) => request<T>("DELETE", path, options),
  upload,
};
