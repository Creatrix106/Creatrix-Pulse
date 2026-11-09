"""Tracks fire-and-forget background tasks (dataset processing).

``asyncio.create_task`` only keeps a *weak* reference to its task, so an un-referenced job can be garbage
collected mid-flight. This registry keeps strong references, lets tests wait for completion, and cancels
whatever is still running on shutdown (those datasets are then reaped as "interrupted" – see datasets.py).
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

log = logging.getLogger(__name__)


class JobRegistry:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def spawn(self, coro: Coroutine[Any, Any, None], *, name: str) -> asyncio.Task[None]:
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    @property
    def running(self) -> int:
        return len(self._tasks)

    async def wait_idle(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        if self._tasks:
            await asyncio.wait_for(asyncio.gather(*self._tasks, return_exceptions=True), timeout)

    async def shutdown(self, timeout: float = 10.0) -> None:  # noqa: ASYNC109
        if not self._tasks:
            return
        _, pending = await asyncio.wait(self._tasks, timeout=timeout)
        for task in pending:
            log.warning("Cancelling unfinished background job %s", task.get_name())
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


jobs = JobRegistry()
