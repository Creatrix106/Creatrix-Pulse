import datetime as dt
from typing import Literal

from pydantic import Field

from app.schemas.common import CamelModel, is_none

DatasetStatus = Literal["uploading", "validating", "processing", "generating", "ready", "failed"]
CanonicalField = Literal["date", "orderId", "product", "category", "region", "customer", "quantity", "revenue", "cost"]
ColumnType = Literal["string", "number", "date", "boolean"]
ProcessingStageId = Literal["upload", "validate", "process", "analytics", "prepare"]
ProcessingStageStatus = Literal["pending", "active", "complete", "failed"]

#: ``ColumnMapping`` in the frontend: canonical field → column header in the uploaded file.
ColumnMapping = dict[CanonicalField, str]


class DatasetCapabilities(CamelModel):
    customers: bool
    cost: bool
    regions: bool


class DatasetColumn(CamelModel):
    name: str
    type: ColumnType
    mapped_to: CanonicalField | None = Field(None, exclude_if=is_none)


class DateRange(CamelModel):
    from_: dt.date = Field(alias="from")
    to: dt.date


class FilterOptions(CamelModel):
    categories: list[str]
    regions: list[str]


class DatasetOut(CamelModel):
    id: str
    name: str
    file_name: str
    file_size: int
    row_count: int
    column_count: int
    status: DatasetStatus
    uploaded_at: dt.datetime
    date_range: DateRange | None
    capabilities: DatasetCapabilities
    columns: list[DatasetColumn]
    filter_options: FilterOptions
    error_message: str | None = Field(None, exclude_if=is_none)


class ProcessingStage(CamelModel):
    id: ProcessingStageId
    label: str
    status: ProcessingStageStatus


class ProcessingStatusOut(CamelModel):
    dataset_id: str
    status: DatasetStatus
    stages: list[ProcessingStage]
    #: Real 0-100 progress of the job, or null. The UI never invents a value.
    progress: int | None
    message: str | None = Field(None, exclude_if=is_none)


class UploadResultOut(CamelModel):
    dataset_id: str
