

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_PSYCOPG_PREFIX = "postgresql+psycopg://"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ------------------------------------------------------------------ application
    app_name: str = "Creatrix Pulse API"
    environment: Literal["development", "test", "production"] = "development"
    #: Routes are mounted below this prefix. The frontend appends its paths to
    #: ``NEXT_PUBLIC_API_BASE_URL``, so that value must be ``<origin><api_prefix>``.
    api_prefix: str = "/api"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    #: Interactive OpenAPI docs. ``None`` = enabled everywhere except production.
    docs_enabled: bool | None = None
    #: Public base URL of the API (e.g. ``https://api.example.com/api``). Only used to
    #: build absolute ``downloadUrl`` values; when unset an origin-relative path is returned.
    public_api_url: str | None = None

    # ------------------------------------------------------------------- database
    #: Any ``postgresql://`` / ``postgres://`` URL is accepted and rewritten to the psycopg 3 driver.
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/app_db"
    db_pool_size: int = Field(10, ge=1, le=100)
    db_max_overflow: int = Field(10, ge=0, le=100)
    db_pool_timeout: float = Field(30.0, gt=0)
    db_echo: bool = False

    # ------------------------------------------------------------- CORS and cookies
    #: Comma separated list (or JSON array) of browser origins allowed to call the API.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    session_cookie_name: str = "cp_session"
    session_ttl_hours: int = Field(24 * 7, ge=1)
    #: ``None`` = secure cookies in production only (they cannot be set over plain http).
    cookie_secure: bool | None = None
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None

    # ------------------------------------------------------------------------ auth
    #: Set to false to close public sign-up (accounts can then only be created directly in the database).
    allow_registration: bool = True
    login_max_failed_attempts: int = Field(10, ge=3)
    login_lock_minutes: int = Field(5, ge=1)

    # ------------------------------------------------------- uploads & processing
    #: Mirrors ``MAX_FILE_SIZE_MB`` in the frontend (src/config/files.ts).
    max_upload_mb: int = Field(25, ge=1, le=500)
    max_rows: int = Field(1_000_000, ge=1)
    max_columns: int = Field(200, ge=1)
    #: Upper bound for an .xlsx once decompressed (zip-bomb protection).
    max_excel_uncompressed_mb: int = Field(400, ge=1)
    #: Ambiguous dates such as 03/04/2026 are read day-first unless the file proves otherwise.
    default_dayfirst: bool = True
    max_concurrent_ingestions: int = Field(2, ge=1)
    #: Uploads a user may have processing at the same time (abuse protection).
    max_active_datasets_per_user: int = Field(3, ge=1)
    #: A dataset that has not reported progress for this long is considered abandoned.
    processing_stale_seconds: int = Field(300, ge=30)
    copy_chunk_rows: int = Field(10_000, ge=100)

    # --------------------------------------------------------------- analytics
    analytics_cache_max_datasets: int = Field(16, ge=1)
    analytics_cache_max_mb: int = Field(512, ge=16)
    #: Default / maximum number of rows returned by ``GET /datasets/:id/records``
    #: (mirrors ``maxRowsInExport`` in src/config/table.ts).
    explorer_max_rows: int = Field(50_000, ge=100)
    #: Defaults for server-formatted text (insights); the UI keeps its own preference.
    default_currency: str = "INR"
    default_locale: str = "en-IN"

    # ----------------------------------------------------------------- validators
    @field_validator("api_prefix")
    @classmethod
    def _normalise_prefix(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value and not value.startswith("/"):
            value = f"/{value}"
        return value

    @field_validator("database_url")
    @classmethod
    def _require_psycopg(cls, value: str) -> str:
        for scheme in ("postgres://", "postgresql://"):
            if value.startswith(scheme):
                return _PSYCOPG_PREFIX + value.removeprefix(scheme)
        if not value.startswith(_PSYCOPG_PREFIX):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL (postgresql://user:pass@host:5432/db).")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):  # NoDecode switches pydantic-settings' own JSON parsing off for this field
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError("CORS_ORIGINS looks like JSON but is not valid JSON.") from exc
                return [str(origin).strip().rstrip("/") for origin in parsed]
            return [origin.strip().rstrip("/") for origin in text.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _check_cookie_policy(self) -> Settings:
        if self.cookie_samesite == "none" and not self.effective_cookie_secure:
            raise ValueError("COOKIE_SAMESITE=none requires secure cookies (COOKIE_SECURE=true).")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must list explicit origins: credentialed requests cannot use '*'.")
        return self

    # ------------------------------------------------------------------- derived
    @property
    def effective_cookie_secure(self) -> bool:
        return self.environment == "production" if self.cookie_secure is None else self.cookie_secure

    @property
    def effective_docs_enabled(self) -> bool:
        return self.environment != "production" if self.docs_enabled is None else self.docs_enabled

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def psycopg_conninfo(self) -> str:
        """libpq connection string for the dedicated COPY connection (no SQLAlchemy driver suffix)."""
        return "postgresql://" + self.database_url.removeprefix(_PSYCOPG_PREFIX)


@lru_cache
def get_settings() -> Settings:
    return Settings()
