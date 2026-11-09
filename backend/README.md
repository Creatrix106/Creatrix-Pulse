# Creatrix Pulse — backend

FastAPI + PostgreSQL + pandas backend for the **Creatrix Pulse** sales-analytics dashboard
(`Creatrix-Pulse--frontend`). It implements the contract in the frontend's
`docs/BACKEND_INTEGRATION.md` endpoint for endpoint, and replaces the in-browser mock engine
(`src/services/mock/*`) with the real thing: users upload a CSV/Excel file, the server validates and cleans it,
stores it in PostgreSQL, and serves KPIs, trends, breakdowns, customer/finance analytics, automatic insights,
records and reports computed with pandas.

> **Verification.** 400+ automated tests run against a real PostgreSQL 18 server, including a **contract test
> that type-checks real responses against the frontend's own TypeScript types with `tsc --strict`** (see
> [Testing](#testing)). `mypy --strict` and `ruff` are clean. The Docker files are written but were **not built**
> in the environment this was developed in (no Docker daemon) — see [Docker](#docker).

## Stack (latest stable as of 2026-11-06, versions pinned in `uv.lock`)

| | Version | Notes |
|---|---|---|
| **Python** | **3.15.2** | 3.15.0 final was released 2026-10-09; every compiled dependency ships `cp315` wheels |
| **FastAPI** | **0.162.0** (Starlette 1.10, Pydantic 2.14) | Pydantic v2 schemas with camelCase aliases matching the TS types |
| **PostgreSQL** | **18** (18.6) | latest *stable* major. **19 is at RC1 and goes GA on 2026-11-19** — see below |
| **pandas** | **3.1.1** (NumPy 2.5, PyArrow 26) | Arrow-backed `str` dtype, Copy-on-Write; no deprecated API is used (tests run with warnings-as-errors) |
| SQLAlchemy | 2.1.8 (async, psycopg 3.3 driver) | typed ORM models, Alembic 1.20 migrations |
| Excel | python-calamine 0.9 (Rust) | reads `.xlsx` **and legacy `.xls`**; no xlrd/openpyxl at runtime |
| Auth | pwdlib 0.3 (Argon2id), server-side sessions | httpOnly cookie |
| i18n | Babel 2.18 (CLDR) | server-written insight text formats like the browser's `Intl` |
| Server | uvicorn 0.54 + uvloop | |
| Tooling | uv 0.13, pytest 9.2, ruff 0.17, mypy 2.4 (+pandas-stubs), TypeScript 5.9.3 | |

**PostgreSQL 19:** it is not generally available yet (RC1 shipped 2026-10-15; GA is scheduled for 2026-11-19), so
this project targets 18. Nothing in the code is version-specific: on 2026-11-19 set `POSTGRES_VERSION=19` for a new
database (an existing volume must be migrated with `pg_upgrade` or dump/restore first).

## Quick start

### Docker

```bash
cp .env.example .env            # optional; every value has a default
docker compose up --build       # PostgreSQL 18 + API on http://localhost:8000 (migrations run on start)
# interactive docs (non-production): http://localhost:8000/api/docs
```

### Local (without Docker for the API)

```bash
uv sync                          # creates .venv with the locked dependencies (fetches Python 3.15 if needed)
docker compose up -d db          # or point DATABASE_URL at any PostgreSQL 16+ server
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

## Connecting the frontend

In the frontend's `.env.local`:

```bash
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api     # <origin> + API_PREFIX
```

* The API sends credentials-enabled CORS headers for the origins in `CORS_ORIGINS` (default
  `http://localhost:3000` and `http://127.0.0.1:3000`) and authenticates with an **httpOnly, `SameSite=Lax`**
  session cookie. **Open the frontend and the API with the same hostname** (`localhost` + `localhost`, or
  `127.0.0.1` + `127.0.0.1`): to a browser `localhost` and `127.0.0.1` are different sites, and a `Lax` cookie is
  not sent across sites.
* Production: serve both from the same site (e.g. `app.example.com` and `api.example.com`) and set
  `ENVIRONMENT=production` (secure cookies). Truly cross-site deployments need `COOKIE_SAMESITE=none` (+ HTTPS),
  and browsers are phasing out third-party cookies, so a same-site setup or a reverse proxy is strongly preferable.
* Alternative without CORS: proxy `/api/*` to the backend with a Next.js `rewrites()` entry and keep
  `NEXT_PUBLIC_API_BASE_URL=/api`. (Not exercised here; check that your proxy accepts 25 MB request bodies.)
* **No frontend code changes are required.** Two optional improvements:
  * Report downloads: the current `download()` in `reports-view.tsx` uses `record.content`, which the API provides
    inline *and* as `downloadUrl` (an authenticated attachment endpoint) — switch to `downloadUrl` when you
    prefer not to ship content in history responses.
  * Insight text is written by the server. It defaults to INR / `en-IN` (what the mock hard-coded); pass
    `currency=USD&locale=en-US` on the analytics calls to follow the user's preference.

## API

All routes live under `API_PREFIX` (default `/api`). Errors always look like `{"code", "message", "details"?}` and
`message` is safe to show to users. Interactive docs: `/api/docs`.

| Method & path | Purpose |
|---|---|
| `POST /auth/register` · `/auth/login` · `/auth/logout` · `GET /auth/me` | account + session cookie (`logout` → 204, `me` → 401 when signed out) |
| `GET /datasets` · `GET /datasets/{id}` · `DELETE /datasets/{id}` | the caller's datasets, newest first |
| `POST /datasets` (multipart: `file`, `mapping` JSON, `replaceDatasetId`) | upload → **202** `{datasetId}`; processing continues in the background |
| `GET /datasets/{id}/processing` | stages + **real** progress, to poll while a dataset is being prepared |
| `GET /datasets/{id}/analytics/{overview,sales,products,customers,finance,insights}` | filters: `datePreset`, `dateFrom`, `dateTo`, `comparison`, `groupBy`, repeated `categories`/`regions` |
| `GET /datasets/{id}/records` | Data Explorer rows, newest first (`limit`/`offset`, capped at 50,000) |
| `POST /datasets/{id}/reports/preview` · `GET`/`POST /datasets/{id}/reports` · `GET …/reports/{rid}/download` | custom reports (CSV/JSON) |
| `GET /health` · `/health/ready` | liveness / readiness (also served at the root `/health`) |

Authorization: every dataset belongs to its owner; another user's dataset is indistinguishable from a missing one
(404). Roles: `admin` (every sign-up; each account is its own workspace) and `analyst` can change data, `viewer`
is read-only.

## How it works

**Upload → ready.** The upload request only stores a `validating` row and returns. A background job then runs
`validate` (parse, map columns, clean every row) → `process` (PostgreSQL `COPY`) → `analytics` (column profile,
filter options) → `prepare` (warm the in-memory frame, mark ready). The dataset row carries `status`, `stage` and
a **real** `progress` (rows written / rows total during the load) plus a heartbeat; a job that stops reporting
(crashed worker) is marked failed by the next read instead of spinning forever. Replacing a dataset deletes the
old one **only after the new one succeeded**. A 22 MB / 292k-row file is ready in ≈ 8 s.

**Cleaning rules** (strict on purpose — nothing is silently dropped or invented):

* CSV: UTF-8 (BOM), Windows-1252 or Latin-1; delimiter `, ; tab |` detected; only *empty* cells are missing
  (`NA` stays "North America"). Rows with more fields than the header are an error (pandas would otherwise shift
  every column); a trailing comma on every row is accepted. Excel: first sheet with data; Excel dates, serial
  numbers and numeric ids are read correctly. Zip-bomb and file-type checks apply.
* Completely empty rows are ignored. Every other row needs a readable **date** and a numeric **revenue**
  (also quantity/cost *if the user mapped them*); otherwise the dataset fails with a message naming the column,
  the number of bad rows and examples (`row 3: “not-a-date”`). Auto-detected (Excel) optional columns that do not
  parse are ignored instead of failing the upload.
* Numbers: `₹1,299.50`, `12,34,567.89`, `(50.00)`, `Rs. 100`; European decimal commas (`1.234,56`) are rejected
  rather than silently mis-read 1000×. Dates: ISO (the calendar day written in the file is kept even with a time
  zone offset), `D/M/Y` vs `M/D/Y` inferred from the column (day-first by default — `DEFAULT_DAYFIRST`), text
  months, `YYYYMMDD`, Excel serials; anything outside 1900–2100 is invalid.
* Blank product/category/region get `Unknown product` / `Uncategorized` / `Unknown` so revenue never vanishes
  from breakdowns; blank customers and order ids stay empty. No quantity → 1 per row; no order id → each row is its
  own order. Profit exists only when the cost column is complete.

**Analytics.** PostgreSQL is the system of record, **pandas is the engine**: a dataset's rows are loaded once into a
compact frame (categorical dimensions, factorised order ids) held in a size-bounded LRU cache (single-flight loading,
so concurrent requests share one read; the ingestion job pre-warms it). Filters/presets/comparison follow the
frontend's engine exactly (presets are relative to the dataset's *latest date*, previous period = equal-length
window before it). Computation runs in worker threads so the event loop stays free. Insights (revenue change,
top category, concentration, movers, unusual week via z-score, regional share, margin, repeat rate) are phrased by
the server with CLDR-correct number/currency/date formats and `toFixed`-compatible rounding.

### Deliberate differences from the frontend mock

1. **Time series are zero-filled** over the window (days without sales are real zeros), and the previous-period
   series keeps buckets from before the data began as zeros, because the UI overlays it *by position*.
2. **Orders are distinct order ids** (real files have several lines per order); "repeat customer" means ≥ 2 distinct
   orders; revenue-per-customer counts only rows that have a customer.
3. Customer distribution is by region only (the mock silently fell back to category).
4. `GET /records` is capped/paged and returns extra fields `total`, `truncated`, `limit`, `offset`.
5. Failed processing keeps the old dataset when replacing; uploads are rejected with a clear message instead of
   dropping bad rows.

## Configuration

Environment variables or `.env` (see `.env.example`). Highlights:

| Variable | Default | |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@127.0.0.1:5432/app_db` | any `postgres(ql)://` URL; psycopg 3 is used |
| `ENVIRONMENT` | `development` | `production` → secure cookies, `/docs` off |
| `API_PREFIX` | `/api` | `NEXT_PUBLIC_API_BASE_URL` = origin + this |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | exact origins; `*` is rejected (cookie auth) |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` / `COOKIE_DOMAIN` | auto / `lax` / – | |
| `MAX_UPLOAD_MB` | `25` | keep equal to `MAX_FILE_SIZE_MB` in the frontend |
| `ALLOW_REGISTRATION` | `true` | `false` closes public sign-up |
| `ANALYTICS_CACHE_MAX_MB` / `_MAX_DATASETS` | `512` / `16` | per worker process |
| `DEFAULT_CURRENCY` / `DEFAULT_LOCALE` / `DEFAULT_DAYFIRST` | `INR` / `en-IN` / `true` | |

## Testing

```bash
export TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/creatrix_test   # created/dropped by the run
uv run pytest                    # everything
make lint                        # ruff;   uv run mypy app   # strict
```

The suite creates the database, applies the **real Alembic migrations**, and drives the real ASGI app:

* `test_analytics_engine` — 200 randomised scenarios compare the pandas engine with an independently written,
  loop-based **reference implementation** of the original TypeScript logic (`tests/reference_engine.py`). (During
  development the suite was also mutation-tested: injecting off-by-one windows, Sunday-start weeks, `>` for `>=`
  and missing zero-fill each made it fail.)
* `test_contract_typescript` — drives every endpoint and capability branch, writes the JSON as typed literals and
  runs **`tsc --strict` against the frontend's `src/types`**, plus negative controls (renamed key, `null` where only
  `undefined` is allowed, bad enum, …). Needs `FRONTEND_TYPES_DIR` and `npm install` in `tests/contract`
  (`make contract`); skipped otherwise.
* API, ingestion (encodings, delimiters, Excel, malformed files, number/date formats), insights (hand-computed
  expectations), reports, security (CORS, CSRF origin check, request ids, size limits, 500s that keep CORS
  headers), robustness (crashes, deletes mid-processing, sign-up race, DB start-up retry), tenant isolation.

`scripts/perf_check.py` uploads a generated ~24 MB CSV to a running server and times everything. Measured on a
1-vCPU sandbox with 292,625 rows: upload request 0.2 s · processing 7.6 s · warm analytics 15–70 ms · first read
after a restart 1.4 s · 50,000-row explorer payload 0.5 s (1.5 MB gzipped) · ≈ 370 MB RSS per worker.

## Operations & security

* **Workers:** `WEB_CONCURRENCY` uvicorn processes; sessions and job state live in PostgreSQL, so any worker can
  serve any request (verified with 2 workers). Frame caches are per process. Behind a proxy set
  `FORWARDED_ALLOW_IPS`.
* **Migrations:** the Docker entrypoint runs `alembic upgrade head`; with several replicas run it once as a job and
  start the replicas with `RUN_MIGRATIONS=false`.
* **Shutdown:** SIGTERM waits (≤ 10 s) for running processing jobs; anything cut off is failed as "interrupted".
* Passwords: Argon2id (upgraded transparently), constant-time login for unknown e-mails, account lock after
  repeated failures. Sessions: 256-bit random token, only its SHA-256 is stored, revocable, sliding expiry.
  CSRF: `SameSite` + `Origin` allow-list on every state-changing request. Uploads: size/type/zip-bomb limits, a cap
  on concurrent uploads per user. Responses are `Cache-Control: no-store`. IP-level rate limiting is left to your
  reverse proxy / WAF.
* Backups: standard PostgreSQL tooling (`pg_dump`/PITR); uploaded files themselves are *not* kept — the cleaned rows are.

## Docker

`Dockerfile` (Python 3.15, locked production-only dependencies, non-root) and `docker-compose.yml` (PostgreSQL 18 —
mounted at `/var/lib/postgresql`, the correct path for 18+ images) are provided. They were **not built or run in the
environment this project was developed in**; what *was* verified: the production-only dependency set installs from
`uv.lock` and imports/migrates on Python 3.15, the entrypoint logic, `.env` parsing, and that the official
`python:3.15-slim-bookworm` tag exists. Expect to confirm `docker compose up --build` on your machine.

## Known limitations

* Only the nine canonical fields are stored; other columns of the file are listed but not kept.
* No password reset / e-mail verification / invitations (the `analyst` and `viewer` roles exist but nothing assigns them).
* Analytics are computed in memory per dataset (sized for the 25 MB upload limit); much larger data would call for
  SQL-side aggregation. Background jobs run in-process (no external queue).

## Layout

```
app/
  api/routes/        auth, datasets, analytics (+records), reports, health
  core/              settings, error model, security, pure-ASGI middleware
  db/                SQLAlchemy 2.1 models (users, auth_sessions, datasets, sales_records, reports)
  schemas/           Pydantic models = the frontend's TypeScript types
  services/
    ingestion/       reader → fields (mapping) → cleaner → profile → loader (COPY) → pipeline
    analytics/       frames (cache) → slicing → metrics → dashboards / insights / explorer / formatting
    auth.py  datasets.py  reports.py  jobs.py
migrations/          Alembic (sync engine, psycopg 3)
tests/               suites above + reference engine + TypeScript contract check
scripts/perf_check.py
```
