import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DATASET_STATUSES = ("uploading", "validating", "processing", "generating", "ready", "failed")
NON_TERMINAL_STATUSES = ("uploading", "validating", "processing", "generating")


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploading', 'validating', 'processing', 'generating', 'ready', 'failed')", name="status_valid"
        ),
        CheckConstraint("progress IS NULL OR progress BETWEEN 0 AND 100", name="progress_range"),
        Index("ix_datasets_owner_id_uploaded_at", "owner_id", "uploaded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(BigInteger)
    row_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    column_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))

    status: Mapped[str] = mapped_column(String(16), default="validating", server_default="validating")
    #: Pipeline stage that is running (or that failed): upload | validate | process | analytics | prepare.
    stage: Mapped[str | None] = mapped_column(String(16))
    #: Real 0-100 progress of the processing job; NULL when not processing.
    progress: Mapped[int | None] = mapped_column(SmallInteger)
    error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    #: Heartbeat – bumped on every progress update; used to detect abandoned jobs.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
    has_customers: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    has_cost: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    has_regions: Mapped[bool] = mapped_column(default=False, server_default=text("false"))

    columns: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    filter_options: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {"categories": [], "regions": []},
        server_default=text("""'{"categories": [], "regions": []}'::jsonb"""),
    )
    #: The effective canonical-field → column mapping used for this dataset.
    mapping: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    #: Dataset to delete once this one finishes processing successfully ("Replace dataset").
    replaces_dataset_id: Mapped[uuid.UUID | None] = mapped_column()


class SalesRecord(Base):
    """One cleaned, canonical row of an uploaded file. Rows are immutable once the dataset is ready."""

    __tablename__ = "sales_records"
    __table_args__ = (Index("ix_sales_records_dataset_id_order_date", "dataset_id", "order_date"),)

    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True)
    #: Row number in the uploaded file (spreadsheet numbering: the header is row 1).
    row_number: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    order_date: Mapped[date] = mapped_column(Date)
    order_id: Mapped[str | None] = mapped_column(Text)
    product: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    customer: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("format IN ('csv', 'json')", name="format_valid"),
        Index("ix_reports_dataset_id_created_at", "dataset_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(8))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content: Mapped[str] = mapped_column(Text)
    row_count: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
