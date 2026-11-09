"""Dataset persistence, ownership checks, lifecycle (stale detection, delete) and API mapping."""

import re
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Conflict, NotFound
from app.db.models import NON_TERMINAL_STATUSES, Dataset, SalesRecord
from app.schemas.dataset import (
    DatasetCapabilities,
    DatasetColumn,
    DatasetOut,
    DateRange,
    FilterOptions,
    ProcessingStage,
    ProcessingStatusOut,
)
from app.services.analytics.frames import get_frame_cache

#: Stage ids/labels shown on the processing page (same order and wording as the frontend mock).
STAGES: tuple[tuple[str, str], ...] = (
    ("upload", "Uploading dataset"),
    ("validate", "Validating columns"),
    ("process", "Processing records"),
    ("analytics", "Generating analytics"),
    ("prepare", "Preparing dashboard"),
)
STAGE_IDS = tuple(stage for stage, _ in STAGES)
#: Dataset status while a given stage is running.
STAGE_STATUS = {"validate": "validating", "process": "processing", "analytics": "generating", "prepare": "generating"}

INTERRUPTED_MESSAGE = "Processing was interrupted before it finished. Please upload the file again."
NOT_FOUND_MESSAGE = "This dataset does not exist or was deleted."


# ------------------------------------------------------------------------------------------ lookup
def parse_dataset_id(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError, AttributeError:
        return None


async def get_owned(session: AsyncSession, owner_id: uuid.UUID, dataset_id: str) -> Dataset:
    """The caller's dataset, or 404. Another user's dataset is indistinguishable from a missing one."""
    parsed = parse_dataset_id(dataset_id)
    dataset = None
    if parsed is not None:
        dataset = await session.scalar(select(Dataset).where(Dataset.id == parsed, Dataset.owner_id == owner_id))
    if dataset is None:
        raise NotFound(NOT_FOUND_MESSAGE, code="dataset_not_found")
    await reap_stale(session, [dataset])
    return dataset


async def get_ready(session: AsyncSession, owner_id: uuid.UUID, dataset_id: str) -> Dataset:
    dataset = await get_owned(session, owner_id, dataset_id)
    if dataset.status != "ready":
        raise Conflict(
            "This dataset is not ready yet." if dataset.status != "failed" else "This dataset failed to process.",
            code="dataset_not_ready",
        )
    return dataset


async def list_for_owner(session: AsyncSession, owner_id: uuid.UUID) -> list[Dataset]:
    result = await session.scalars(
        select(Dataset).where(Dataset.owner_id == owner_id).order_by(Dataset.uploaded_at.desc(), Dataset.id.desc())
    )
    datasets = list(result)
    await reap_stale(session, datasets)
    return datasets


# ----------------------------------------------------------------------------------------- lifecycle
def derive_name(file_name: str) -> str:
    stem = re.sub(r"\.[^.]+$", "", file_name)  # same rule as the frontend mock
    name = re.sub(r"[_-]+", " ", stem).strip()
    return (name or "Untitled dataset")[:255]


def safe_file_name(raw: str | None) -> str:
    """Base name only, without control characters (clients may send a full client-side path)."""
    name = PureWindowsPath(PurePosixPath(raw or "").name).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return (name or "upload")[-255:]


async def create_pending(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    file_name: str,
    file_size: int,
    mapping: dict[str, str],
    replaces: uuid.UUID | None,
) -> Dataset:
    dataset = Dataset(
        owner_id=owner_id,
        name=derive_name(file_name),
        file_name=file_name,
        file_size=file_size,
        status="validating",
        stage="validate",
        progress=0,
        mapping=mapping,
        replaces_dataset_id=replaces,
    )
    session.add(dataset)
    await session.commit()
    return dataset


async def delete_dataset(session: AsyncSession, dataset_id: uuid.UUID) -> None:
    # sales_records / reports go with it (ON DELETE CASCADE).
    await session.execute(delete(Dataset).where(Dataset.id == dataset_id))
    await session.commit()
    get_frame_cache().evict(dataset_id)


async def reap_stale(session: AsyncSession, datasets: Iterable[Dataset]) -> None:
    """Fail datasets whose processing job stopped reporting progress (e.g. the server restarted mid-job).

    The job bumps ``updated_at`` on every step, so silence for ``processing_stale_seconds`` means it is gone.
    The UPDATE is guarded by the heartbeat we observed, so it can never fail a job that just made progress.
    """
    threshold = get_settings().processing_stale_seconds
    now = datetime.now(UTC)
    reaped = False
    for dataset in datasets:
        if dataset.status in NON_TERMINAL_STATUSES and (now - dataset.updated_at).total_seconds() > threshold:
            result = await session.execute(
                update(Dataset)
                .where(
                    Dataset.id == dataset.id,
                    Dataset.status.in_(NON_TERMINAL_STATUSES),
                    Dataset.updated_at == dataset.updated_at,
                )
                .values(
                    status="failed",
                    progress=None,
                    row_count=0,
                    error_message=INTERRUPTED_MESSAGE,
                    updated_at=func.now(),
                )
            )
            if cast(CursorResult[Any], result).rowcount:
                await session.execute(delete(SalesRecord).where(SalesRecord.dataset_id == dataset.id))
                reaped = True
    if reaped:
        await session.commit()
        for dataset in datasets:
            await session.refresh(dataset)


# ------------------------------------------------------------------------------------ API mapping
def to_out(dataset: Dataset) -> DatasetOut:
    has_range = dataset.date_from is not None and dataset.date_to is not None
    return DatasetOut(
        id=str(dataset.id),
        name=dataset.name,
        file_name=dataset.file_name,
        file_size=dataset.file_size,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        status=dataset.status,
        uploaded_at=dataset.uploaded_at,
        date_range=DateRange(from_=dataset.date_from, to=dataset.date_to) if has_range else None,
        capabilities=DatasetCapabilities(
            customers=dataset.has_customers, cost=dataset.has_cost, regions=dataset.has_regions
        ),
        columns=[DatasetColumn.model_validate(column) for column in dataset.columns],
        filter_options=FilterOptions.model_validate(
            {"categories": [], "regions": [], **(dataset.filter_options or {})}
        ),
        error_message=dataset.error_message if dataset.status == "failed" else None,
    )


def to_processing_status(dataset: Dataset) -> ProcessingStatusOut:
    position = STAGE_IDS.index(dataset.stage) if dataset.stage in STAGE_IDS else 1
    if dataset.status == "ready":
        states = ["complete"] * len(STAGES)
    elif dataset.status == "failed":
        states = ["complete"] * position + ["failed"] + ["pending"] * (len(STAGES) - position - 1)
    else:
        states = ["complete"] * position + ["active"] + ["pending"] * (len(STAGES) - position - 1)
    failed = dataset.status == "failed"
    return ProcessingStatusOut(
        dataset_id=str(dataset.id),
        status=dataset.status,
        stages=[
            ProcessingStage(id=stage_id, label=label, status=state)
            for (stage_id, label), state in zip(STAGES, states, strict=True)
        ],
        progress=100 if dataset.status == "ready" else (None if failed else dataset.progress),
        message=dataset.error_message if failed else None,
    )
