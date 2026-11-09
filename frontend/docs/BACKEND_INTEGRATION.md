# Creatrix Pulse backend integration

The frontend calls the backend through `src/services/*.service.ts` and `src/services/api-client.ts`.
Configure `NEXT_PUBLIC_API_BASE_URL` at build time as the backend root (default `/api`, for a same-origin reverse proxy). For a separate API host, use its HTTPS origin and API prefix, such as `https://api.example.com/v1`.

`NEXT_PUBLIC_API_BASE_URL` is included in browser code. It must contain only the public API URL; never put credentials, tokens, or other secrets in any `NEXT_PUBLIC_` variable. Requests include credentials for the httpOnly session cookie. Cross-origin deployments must configure the backend to allow the exact frontend origin with credentials and set the session cookie attributes for the deployment (including `Secure` on HTTPS and a compatible `SameSite` policy).

Errors are expected as `{ "code": string, "message": string, "details"?: unknown }` with an appropriate HTTP status.

## Auth

- `POST /auth/login` `{ email, password }` -> `User` and session cookie
- `POST /auth/register` `{ name, email, password }` -> `User`
- `POST /auth/logout` -> `204`
- `GET /auth/me` -> `User` (`401` when signed out)

## Datasets

- `GET /datasets` -> `Dataset[]`
- `GET /datasets/:id` -> `Dataset` (`404` when missing)
- `DELETE /datasets/:id` -> `204`
- `POST /datasets` multipart fields: `file`, `mapping` (JSON `ColumnMapping`), optional `replaceDatasetId`; response `{ datasetId }`
- `GET /datasets/:id/processing` -> `ProcessingStatus`; poll every 1.2 seconds until `ready` or `failed`. `progress` is a real 0-100 number or `null`.

## Analytics

Analytics endpoints accept `datePreset`, `dateFrom`, `dateTo`, `comparison`, `groupBy`, repeated `categories`, and repeated `regions` query parameters.

- `GET /datasets/:id/analytics/overview` -> `OverviewData`
- `GET /datasets/:id/analytics/sales` -> `SalesData`
- `GET /datasets/:id/analytics/products` -> `ProductsData`
- `GET /datasets/:id/analytics/customers` -> `Capability<CustomersData>`
- `GET /datasets/:id/analytics/finance` -> `Capability<FinanceData>`
- `GET /datasets/:id/analytics/insights` -> `Insight[]`
- `GET /datasets/:id/records` -> `ExplorerData`

Customers and finance may return `{ available: false, reason }` when required columns are absent. The explorer currently searches, filters, sorts, and paginates the returned rows client-side; no server paging request contract is defined here.

## Reports

- `POST /datasets/:id/reports/preview` `ReportConfig` -> `ReportPreview`
- `GET /datasets/:id/reports` -> `ReportRecord[]`
- `POST /datasets/:id/reports` `ReportConfig` -> `ReportRecord` with `downloadUrl`

Types and request construction are defined in `src/types/` and the corresponding service modules.
