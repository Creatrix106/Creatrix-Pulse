"""Dataset processing pipeline: file bytes → validated rows in PostgreSQL → ready dataset.

Runs as a background task after the upload response has been sent. Every step reports *real* progress by
updating the dataset row (status / stage / progress / heartbeat), which the processing page polls.

    validate  (0 → 15 %)   parse the file, map columns, validate and clean every row
    process   (15 → 85 %)  COPY the clean rows into PostgreSQL, progress = rows written / rows total
    analytics (88 %)       column profile, filter options, capabilities
    prepare   (96 → 100 %) warm the analytics cache, mark ready, drop the dataset this one replaces

Any failure marks the dataset ``failed`` with a user-facing message and removes partial rows.
"""

import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy import delete, func, select, update

from app.core.config import get_settings
from app.db.models import Dataset, SalesRecord
from app.db.session import get_sessionmaker
from app.services.analytics.frames import build_frame, get_frame_cache
from app.services.datasets import STAGE_STATUS
from app.services.ingestion.cleaner import clean_table
from app.services.ingestion.errors import IngestionError
from app.services.ingestion.fields import resolve_mapping
from app.services.ingestion.loader import copy_records
from app.services.ingestion.profile import build_columns, build_filter_options
from app.services.ingestion.reader import read_table

log = logging.getLogger(__name__)

UNEXPECTED_FAILURE = (
    "Something went wrong while processing this file. Please try again, and contact support if it keeps happening."
)
_PROCESS_FROM, _PROCESS_TO = 15, 85

_slots: asyncio.Semaphore | None = None
_slots_loop: asyncio.AbstractEventLoop | None = None


def _concurrency_slot() -> asyncio.Semaphore:
    """At most ``max_concurrent_ingestions`` jobs per process: each holds the file plus several DataFrames."""
    global _slots, _slots_loop
    loop = asyncio.get_running_loop()
    if _slots is None or _slots_loop is not loop:
        _slots, _slots_loop = asyncio.Semaphore(get_settings().max_concurrent_ingestions), loop
    return _slots


async def _update(dataset_id: uuid.UUID, **values: Any) -> None:
    """Short, independent transaction: progress must be visible to pollers immediately."""
    async with get_sessionmaker()() as session:
        await session.execute(update(Dataset).where(Dataset.id == dataset_id).values(updated_at=func.now(), **values))
        await session.commit()


async def _enter_stage(dataset_id: uuid.UUID, stage: str, progress: int, **values: Any) -> None:
    await _update(dataset_id, stage=stage, status=STAGE_STATUS[stage], progress=progress, **values)


async def process_dataset(
    *, dataset_id: uuid.UUID, data: bytes, file_name: str, provided_mapping: dict[str, str] | None
) -> None:
    async with _concurrency_slot():
        try:
            await _run(dataset_id, data, file_name, provided_mapping)
        except IngestionError as exc:
            log.info("Dataset %s rejected: %s", dataset_id, exc)
            await _fail(dataset_id, str(exc))
        except asyncio.CancelledError:
            raise  # shutting down; the dataset is reaped as "interrupted" once its heartbeat goes stale
        except Exception:
            log.exception("Dataset %s failed unexpectedly", dataset_id)
            await _fail(dataset_id, UNEXPECTED_FAILURE)


async def _run(dataset_id: uuid.UUID, data: bytes, file_name: str, provided_mapping: dict[str, str] | None) -> None:
    settings = get_settings()

    # ----------------------------------------------------------------------------- validate
    await _enter_stage(dataset_id, "validate", 3)
    parsed = await asyncio.to_thread(
        read_table,
        data,
        file_name,
        max_rows=settings.max_rows,
        max_columns=settings.max_columns,
        max_uncompressed_bytes=settings.max_excel_uncompressed_mb * 1024 * 1024,
    )
    mapping = resolve_mapping(list(parsed.frame.columns), provided_mapping)
    await _update(dataset_id, progress=8, row_count=len(parsed.frame), column_count=len(parsed.frame.columns))

    cleaned = await asyncio.to_thread(
        clean_table,
        parsed,
        mapping,
        auto_mapped=not provided_mapping,
        default_dayfirst=settings.default_dayfirst,
    )
    columns = await asyncio.to_thread(build_columns, parsed, cleaned.mapping)
    row_count, column_count = len(cleaned.frame), len(parsed.frame.columns)
    del parsed, data  # release the raw table and file bytes before loading

    # ------------------------------------------------------------------------------ process
    await _enter_stage(dataset_id, "process", _PROCESS_FROM, row_count=row_count)
    last_reported = _PROCESS_FROM

    async def on_progress(done: int, total: int) -> None:
        nonlocal last_reported
        progress = _PROCESS_FROM + int((_PROCESS_TO - _PROCESS_FROM) * done / total)
        if progress > last_reported:
            last_reported = progress
            await _update(dataset_id, progress=progress)

    await copy_records(
        settings.psycopg_conninfo,
        dataset_id,
        cleaned.frame,
        chunk_rows=settings.copy_chunk_rows,
        on_progress=on_progress,
    )

    # ---------------------------------------------------------------------------- analytics
    await _enter_stage(dataset_id, "analytics", 88)
    filter_options = await asyncio.to_thread(build_filter_options, cleaned.frame)
    analytics_frame = await asyncio.to_thread(build_frame, cleaned.frame)

    # ------------------------------------------------------------------------------ prepare
    await _enter_stage(dataset_id, "prepare", 96)
    get_frame_cache().put(dataset_id, analytics_frame)  # first dashboard view needs no database read
    replaced = await _finalize(
        dataset_id,
        row_count=row_count,
        column_count=column_count,
        columns=columns,
        filter_options=filter_options,
        mapping=cleaned.mapping,
        date_from=cleaned.date_from,
        date_to=cleaned.date_to,
        has_customers=cleaned.capabilities.customers,
        has_cost=cleaned.capabilities.cost,
        has_regions=cleaned.capabilities.regions,
    )
    if replaced is not None:
        get_frame_cache().evict(replaced)


async def _finalize(dataset_id: uuid.UUID, **metadata: Any) -> uuid.UUID | None:
    """Mark the dataset ready and, in the same transaction, delete the dataset it replaces."""
    async with get_sessionmaker()() as session:
        dataset = await session.scalar(select(Dataset).where(Dataset.id == dataset_id))
        if dataset is None:  # deleted by the user while it was processing
            return None
        replaced = dataset.replaces_dataset_id
        await session.execute(
            update(Dataset)
            .where(Dataset.id == dataset_id)
            .values(
                status="ready",
                stage="prepare",
                progress=100,
                error_message=None,
                replaces_dataset_id=None,
                updated_at=func.now(),
                **metadata,
            )
        )
        if replaced is not None:  # only ever the same owner's dataset
            await session.execute(delete(Dataset).where(Dataset.id == replaced, Dataset.owner_id == dataset.owner_id))
        await session.commit()
        return replaced


async def _fail(dataset_id: uuid.UUID, message: str) -> None:
    try:
        async with get_sessionmaker()() as session:
            await session.execute(delete(SalesRecord).where(SalesRecord.dataset_id == dataset_id))
            await session.execute(
                update(Dataset)
                .where(Dataset.id == dataset_id)
                .values(
                    status="failed",
                    progress=None,
                    row_count=0,
                    date_from=None,
                    date_to=None,
                    error_message=message[:2000],
                    updated_at=func.now(),
                )  # `stage` keeps pointing at the stage that failed
            )
            await session.commit()
    except Exception:
        log.exception("Could not record the failure of dataset %s", dataset_id)
    get_frame_cache().evict(dataset_id)
