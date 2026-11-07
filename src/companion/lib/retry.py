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
TOO_MANY_REQUESTS = 429
SERVER_ERROR = 500


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


def transient(err: Exception) -> bool:
    """Whether an error says nothing about the request itself: a dropped connection, a timeout, a
    rate limit or a server error. A refusal or a bad request (any other status) does not."""
    if isinstance(err, httpx.HTTPStatusError):
        status = err.response.status_code
        return status == TOO_MANY_REQUESTS or status >= SERVER_ERROR
    return isinstance(err, httpx.TransportError)


async def retry_transient[T](
    call: Callable[[], Awaitable[T]], delays: Sequence[float], what: str = "call"
) -> T:
    """Like `retry_on_network_error`, and a rate limit or a server error is retried too: for a
    provider that rate-limits, such as a free model. Any other failure is raised at once."""
    for delay in delays:
        try:
            return await call()
        except httpx.HTTPError as err:
            if not transient(err):
                raise
            log.warning("%s: %s, retrying in %.1fs", what, type(err).__name__, delay)
            await asyncio.sleep(delay)
    return await call()
