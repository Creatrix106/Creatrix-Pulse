/**
 * Environment-driven configuration. The API base URL is the ONLY place a backend
 * location is defined; never hardcode URLs elsewhere.
 *
 *   NEXT_PUBLIC_API_BASE_URL – public backend root, e.g. https://api.creatrix.app/v1
 * This value is embedded in the client bundle and must never contain credentials or secrets.
 */
const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
const apiBaseUrl = (configuredApiBaseUrl || "/api").replace(/\/+$/, "") || "/api";

if (apiBaseUrl.startsWith("//")) {
  throw new Error("NEXT_PUBLIC_API_BASE_URL must be a same-origin path or an absolute HTTP(S) URL.");
}

if (!apiBaseUrl.startsWith("/")) {
  let parsedApiUrl: URL;
  try {
    parsedApiUrl = new URL(apiBaseUrl);
  } catch {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be a same-origin path or an absolute HTTP(S) URL.");
  }
  if (parsedApiUrl.protocol !== "http:" && parsedApiUrl.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must use HTTP or HTTPS.");
  }
  if (process.env.NODE_ENV === "production" && parsedApiUrl.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must use HTTPS in production.");
  }
}

export const env = { apiBaseUrl } as const;
