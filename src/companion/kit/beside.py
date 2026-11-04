"""Work that runs beside a turn and never holds up the reply: shadow look-ups and checks after it,
each kept from collection until it ends, a failure logged, never raised and never silent."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine

log = logging.getLogger("companion.turn")


_BESIDE: set[asyncio.Task[None]] = set()  # shadow look-ups still running, kept from collection


def beside(job: Coroutine[object, object, None]) -> None:
    """Run a shadow look-up beside the turn, kept from collection until it ends. A failure is
    logged, never raised and never silent."""
    task = asyncio.get_running_loop().create_task(job)
    _BESIDE.add(task)

    def done(finished: asyncio.Task[None]) -> None:
        _BESIDE.discard(finished)
        if not finished.cancelled() and finished.exception() is not None:
            log.warning("shadow look-up failed: %r", finished.exception())

    task.add_done_callback(done)


async def settled() -> None:
    """Wait for what is running beside the turns to end (for tests and a clean stop)."""
    while _BESIDE:
        await asyncio.gather(*_BESIDE, return_exceptions=True)
