"""Failure paths: the things that go wrong in production rather than in demos."""

import asyncio
import io
import uuid
import zipfile
from datetime import timedelta

import pytest
from app.db.base import utcnow
from app.db.models import AuthSession, Dataset, SalesRecord
from app.db.session import get_sessionmaker
from app.services import auth as auth_service
from app.services.ingestion import pipeline
from app.services.ingestion.errors import IngestionError
from app.services.ingestion.reader import read_table
from app.services.jobs import JobRegistry, jobs
from sqlalchemy import func, select

from tests.conftest import new_client
from tests.helpers import FULL_MAPPING, db_totals, sales_csv, upload, upload_and_wait

LIMITS = dict(max_rows=10**6, max_columns=200, max_uncompressed_bytes=400 * 2**20)


# ---------------------------------------------------------------------------------------- pipeline
async def test_an_unexpected_crash_fails_the_dataset_with_a_generic_message_and_no_internals(
    client, monkeypatch, caplog
):
    def explode(*args, **kwargs):
        raise RuntimeError("secret internal detail: password=hunter2")

    monkeypatch.setattr(pipeline, "read_table", explode)
    ds = await upload_and_wait(client, sales_csv(days=20), mapping=FULL_MAPPING)
    assert ds["status"] == "failed"
    assert ds["errorMessage"] == pipeline.UNEXPECTED_FAILURE
    assert "hunter2" not in ds["errorMessage"]
    assert "hunter2" in caplog.text  # ...but the operator still gets the full traceback in the logs
    status = (await client.get(f"/api/datasets/{ds['id']}/processing")).json()
    assert status["status"] == "failed" and [s["status"] for s in status["stages"]][1] == "failed"


async def test_deleting_a_dataset_while_it_is_processing_is_harmless(client, monkeypatch):
    from app.services.ingestion.loader import copy_records as real_copy

    gate = asyncio.Event()

    async def delayed_copy(*args, **kwargs):
        await gate.wait()  # the user deletes the dataset before any row is written
        return await real_copy(*args, **kwargs)

    monkeypatch.setattr(pipeline, "copy_records", delayed_copy)
    response = await upload(client, sales_csv(days=30), mapping=FULL_MAPPING)
    dataset_id = response.json()["datasetId"]
    await asyncio.sleep(0.3)
    assert (await client.delete(f"/api/datasets/{dataset_id}")).status_code == 204
    gate.set()
    await jobs.wait_idle(timeout=30)  # the job ends quietly: foreign-key violation -> failure path -> nothing to update

    assert (await client.get(f"/api/datasets/{dataset_id}")).status_code == 404
    assert (await db_totals(dataset_id))[0] == 0  # no orphaned rows
    assert (await client.get("/api/datasets")).json() == []


async def test_a_dataset_deleted_just_before_finalising_does_not_crash_the_job(client, monkeypatch):
    original = pipeline._finalize

    async def delete_then_finalize(dataset_id, **metadata):
        async with get_sessionmaker()() as session:
            await session.execute(Dataset.__table__.delete().where(Dataset.id == dataset_id))
            await session.commit()
        return await original(dataset_id, **metadata)

    monkeypatch.setattr(pipeline, "_finalize", delete_then_finalize)
    response = await upload(client, sales_csv(days=20), mapping=FULL_MAPPING)
    await jobs.wait_idle(timeout=30)
    assert (await client.get(f"/api/datasets/{response.json()['datasetId']}")).status_code == 404


async def test_a_failure_while_recording_a_failure_is_survivable(monkeypatch, caplog):
    class Broken:
        async def __aenter__(self):
            raise ConnectionError("database gone")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(pipeline, "get_sessionmaker", lambda: lambda: Broken())
    await pipeline._fail(uuid.uuid4(), "message")  # must not raise
    assert "Could not record the failure" in caplog.text


# --------------------------------------------------------------------------------------- job registry
async def test_job_registry_cancels_unfinished_jobs_on_shutdown():
    registry = JobRegistry()
    finished, cancelled = asyncio.Event(), asyncio.Event()

    async def quick():
        finished.set()

    async def forever():
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    registry.spawn(quick(), name="quick")
    registry.spawn(forever(), name="forever")
    assert registry.running == 2
    await registry.shutdown(timeout=0.2)
    assert finished.is_set() and cancelled.is_set() and registry.running == 0
    await registry.shutdown(timeout=0.2)  # idempotent
    await registry.wait_idle(timeout=1)


# ------------------------------------------------------------------------------------------ Excel files
def test_corrupt_and_empty_workbooks_are_reported_clearly():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:  # a valid zip that is not a workbook
        archive.writestr("[Content_Types].xml", "not xml at all")
    with pytest.raises(IngestionError, match="couldn't read this Excel file"):
        read_table(buffer.getvalue(), "broken.xlsx", **LIMITS)

    import openpyxl

    empty = io.BytesIO()
    openpyxl.Workbook().save(empty)  # one sheet, no cells
    with pytest.raises(IngestionError, match="The workbook has no data"):
        read_table(empty.getvalue(), "empty.xlsx", **LIMITS)


# ----------------------------------------------------------------------------------------------- auth
async def test_concurrent_registrations_of_one_email_create_exactly_one_account(app):
    payload = {"name": "Race Condition", "email": "race@example.com", "password": "Passw0rdOK"}
    async with new_client(app) as a, new_client(app) as b:
        first, second = await asyncio.gather(
            a.post("/api/auth/register", json=payload), b.post("/api/auth/register", json=payload)
        )
    assert sorted([first.status_code, second.status_code]) == [201, 409]
    loser = first if first.status_code == 409 else second
    assert loser.json()["code"] == "email_taken"


async def test_expired_sessions_are_purged(client):
    async with get_sessionmaker()() as session:
        user_id = (await session.scalars(select(AuthSession.user_id))).first()
        session.add(AuthSession(user_id=user_id, token_hash="x" * 64, expires_at=utcnow() - timedelta(days=1)))
        await session.commit()
        assert await session.scalar(select(func.count()).select_from(AuthSession)) == 2
        await auth_service.purge_expired_sessions(session)
        assert await session.scalar(select(func.count()).select_from(AuthSession)) == 1  # the live one survives


# -------------------------------------------------------------------------------------- start-up / config
async def test_startup_waits_for_a_database_that_is_still_booting(monkeypatch):
    import app.main as main

    attempts = 0

    class Flaky:
        async def __aenter__(self):
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("starting up")
            return self

        async def __aexit__(self, *exc):
            return False

        async def execute(self, *args):
            return None

    monkeypatch.setattr(main, "get_sessionmaker", lambda: lambda: Flaky())
    await main._wait_for_database(attempts=5, delay=0)
    assert attempts == 3


async def test_startup_gives_up_loudly_when_the_database_never_comes_up(monkeypatch):
    import app.main as main

    class Down:
        async def __aenter__(self):
            raise ConnectionError("refused")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(main, "get_sessionmaker", lambda: lambda: Down())
    with pytest.raises(RuntimeError, match="Cannot connect to the database"):
        await main._wait_for_database(attempts=2, delay=0)


def test_cors_origins_json_must_be_valid():
    from app.core.config import Settings
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="not valid JSON"):
        Settings(cors_origins='["http://a.test"')


async def test_malformed_content_length_is_a_400(app):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "method": "POST", "path": "/api/auth/login", "raw_path": b"/api/auth/login", "query_string": b"",
        "headers": [(b"content-length", b"abc"), (b"host", b"localhost")], "client": ("127.0.0.1", 1), "scheme": "http",
        "server": ("localhost", 8000), "http_version": "1.1", "root_path": "",
    }  # fmt: skip
    await app(scope, receive, send)
    assert sent[0]["status"] == 400


async def test_orphaned_sales_records_cannot_exist(client):
    """The foreign key (ON DELETE CASCADE) is the guarantee behind every delete/replace flow."""
    ds = await upload_and_wait(client, sales_csv(days=20), mapping=FULL_MAPPING)
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(func.count()).select_from(SalesRecord)) > 0
    await client.delete(f"/api/datasets/{ds['id']}")
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(func.count()).select_from(SalesRecord)) == 0
