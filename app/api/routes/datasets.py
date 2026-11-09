from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, select

from app.api.deps import CurrentUser, SessionDep, WriterUser
from app.core.config import get_settings
from app.core.errors import PayloadTooLarge, TooManyRequests, Unprocessable, UnsupportedMediaType
from app.db.models import NON_TERMINAL_STATUSES, Dataset
from app.schemas.dataset import ColumnMapping, DatasetOut, ProcessingStatusOut, UploadResultOut
from app.services import datasets as dataset_service
from app.services.ingestion.pipeline import process_dataset
from app.services.ingestion.reader import file_kind
from app.services.jobs import jobs

router = APIRouter(prefix="/datasets", tags=["datasets"])

_mapping_adapter = TypeAdapter(ColumnMapping)


def _parse_mapping(raw: str) -> dict[str, str]:
    """The ``mapping`` form field: a JSON object ``{canonicalField: columnHeader}``; ``{}``/empty for Excel."""
    if not raw.strip():
        return {}
    try:
        mapping = _mapping_adapter.validate_json(raw)
    except ValidationError:
        raise Unprocessable(
            'The column mapping is not valid. Expected a JSON object such as {"date": "Order Date"}.',
            code="invalid_mapping",
        ) from None
    cleaned: dict[str, str] = {field: column.strip() for field, column in mapping.items() if column and column.strip()}
    return cleaned


@router.get("", response_model=list[DatasetOut], summary="List the caller's datasets, newest first")
async def list_datasets(user: CurrentUser, session: SessionDep) -> list[DatasetOut]:
    return [dataset_service.to_out(d) for d in await dataset_service.list_for_owner(session, user.id)]


@router.post(
    "",
    response_model=UploadResultOut,
    status_code=202,
    summary="Upload a CSV/Excel file (multipart). Processing continues in the background",
)
async def upload_dataset(
    user: WriterUser,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="The .csv, .xlsx or .xls file")],
    mapping: Annotated[str, Form(description="JSON column mapping; empty for Excel (columns are detected)")] = "",
    replace_dataset_id: Annotated[str | None, Form(alias="replaceDatasetId")] = None,
) -> UploadResultOut:
    settings = get_settings()
    file_name = dataset_service.safe_file_name(file.filename)
    if file_kind(file_name) is None:
        raise UnsupportedMediaType(
            "Unsupported file type. Upload a .csv, .xlsx or .xls file.", code="unsupported_file_type"
        )

    data = await file.read()
    if not data:
        raise Unprocessable("The file is empty.", code="empty_file")
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLarge(
            f"This file is {len(data) / 1024 / 1024:.1f} MB. The maximum size is {settings.max_upload_mb} MB.",
            code="file_too_large",
        )
    provided_mapping = _parse_mapping(mapping)

    active = await session.scalar(
        select(func.count())
        .select_from(Dataset)
        .where(Dataset.owner_id == user.id, Dataset.status.in_(NON_TERMINAL_STATUSES))
    )
    if (active or 0) >= settings.max_active_datasets_per_user:
        raise TooManyRequests(
            "You already have several files processing. Wait for them to finish, then upload again.",
            code="too_many_uploads",
        )

    # "Replace dataset": the old one is removed only after this upload processed successfully. An unknown or
    # foreign id is ignored rather than failing the upload (nothing is lost and nothing is revealed).
    replaces = None
    if replace_dataset_id and (parsed := dataset_service.parse_dataset_id(replace_dataset_id)):
        replaces = await session.scalar(select(Dataset.id).where(Dataset.id == parsed, Dataset.owner_id == user.id))

    dataset = await dataset_service.create_pending(
        session,
        owner_id=user.id,
        file_name=file_name,
        file_size=len(data),
        mapping=provided_mapping,
        replaces=replaces,
    )
    jobs.spawn(
        process_dataset(
            dataset_id=dataset.id, data=data, file_name=file_name, provided_mapping=provided_mapping or None
        ),
        name=f"dataset-{dataset.id}",
    )
    return UploadResultOut(dataset_id=str(dataset.id))


@router.get("/{dataset_id}", response_model=DatasetOut, summary="One dataset")
async def get_dataset(dataset_id: str, user: CurrentUser, session: SessionDep) -> DatasetOut:
    return dataset_service.to_out(await dataset_service.get_owned(session, user.id, dataset_id))


@router.get(
    "/{dataset_id}/processing",
    response_model=ProcessingStatusOut,
    summary="Processing stages and real progress (poll this while a dataset is being prepared)",
)
async def get_processing_status(dataset_id: str, user: CurrentUser, session: SessionDep) -> ProcessingStatusOut:
    return dataset_service.to_processing_status(await dataset_service.get_owned(session, user.id, dataset_id))


@router.delete("/{dataset_id}", status_code=204, summary="Delete a dataset with its records and reports")
async def delete_dataset(dataset_id: str, user: WriterUser, session: SessionDep) -> Response:
    dataset = await dataset_service.get_owned(session, user.id, dataset_id)
    await dataset_service.delete_dataset(session, dataset.id)
    return Response(status_code=204)
