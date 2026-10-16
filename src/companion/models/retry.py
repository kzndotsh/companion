"""Retry a call a few times when the network drops, and only then.

A failed connection says nothing about the request, so repeating it is safe. A refusal, a bad
request or a model error is a real answer and is never retried here.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence

import httpx

log = logging.getLogger("companion.retry")


async def retry_on_network_error[T](
    call: Callable[[], Awaitable[T]], delays: Sequence[float] = (0.5, 1.5), what: str = "call"
) -> T:
    """Run `call`; on a dropped connection or a timeout wait and run it again, once per delay."""
    for delay in delays:
        try:
            return await call()
        except httpx.TransportError as err:
            log.warning(
                "%s: network error (%s), retrying in %.1fs", what, type(err).__name__, delay
            )
            await asyncio.sleep(delay)
    return await call()
