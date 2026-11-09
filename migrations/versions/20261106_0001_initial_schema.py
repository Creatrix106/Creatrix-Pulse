"""initial schema

Revision ID: 0001
Revises:
Create Date: meri marji
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="admin", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'analyst', 'viewer')", name=op.f("ck_users_role_valid")),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_email_lowercase")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_auth_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_sessions_token_hash")),
    )
    op.create_index(op.f("ix_auth_sessions_expires_at"), "auth_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)
    op.create_table(
        "datasets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("row_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("column_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="validating", nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=True),
        sa.Column("progress", sa.SmallInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("has_customers", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("has_cost", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("has_regions", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "columns",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "filter_options",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text('\'{"categories": [], "regions": []}\'::jsonb'),
            nullable=False,
        ),
        sa.Column(
            "mapping",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("replaces_dataset_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "status IN ('uploading', 'validating', 'processing', 'generating', 'ready', 'failed')",
            name=op.f("ck_datasets_status_valid"),
        ),
        sa.CheckConstraint("progress IS NULL OR progress BETWEEN 0 AND 100", name=op.f("ck_datasets_progress_range")),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_datasets_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datasets")),
    )
    op.create_index("ix_datasets_owner_id_uploaded_at", "datasets", ["owner_id", "uploaded_at"], unique=False)
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("format IN ('csv', 'json')", name=op.f("ck_reports_format_valid")),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["datasets.id"], name=op.f("fk_reports_dataset_id_datasets"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_reports_owner_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
    )
    op.create_index("ix_reports_dataset_id_created_at", "reports", ["dataset_id", "created_at"], unique=False)
    op.create_table(
        "sales_records",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("order_id", sa.Text(), nullable=True),
        sa.Column("product", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("customer", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("cost", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_sales_records_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("dataset_id", "row_number", name=op.f("pk_sales_records")),
    )
    op.create_index(
        "ix_sales_records_dataset_id_order_date", "sales_records", ["dataset_id", "order_date"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_sales_records_dataset_id_order_date", table_name="sales_records")
    op.drop_table("sales_records")
    op.drop_index("ix_reports_dataset_id_created_at", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_datasets_owner_id_uploaded_at", table_name="datasets")
    op.drop_table("datasets")
    op.drop_index(op.f("ix_auth_sessions_user_id"), table_name="auth_sessions")
    op.drop_index(op.f("ix_auth_sessions_expires_at"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("users")
