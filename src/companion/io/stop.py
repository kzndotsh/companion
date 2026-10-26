"""Stopping without losing a message: on SIGTERM or SIGINT the bot fetches nothing more and answers
what it already received, the reply in progress included, before it exits. A restart once stopped it
mid-turn and lost a message that had been received (2026-10-25)."""

from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable

log = logging.getLogger("companion")
GRACE_SECONDS = 30  # how long the reply in progress may take to go out after a stop


async def until_stopped(serve: Callable[[asyncio.Event], Awaitable[None]]) -> None:
    """Serve until SIGTERM or SIGINT, then let what was received be answered before returning, for
    at most GRACE_SECONDS (`just restart` waits for it)."""
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    serving = asyncio.ensure_future(serve(stop))
    stopping = asyncio.ensure_future(stop.wait())
    await asyncio.wait({serving, stopping}, return_when=asyncio.FIRST_COMPLETED)
    stopping.cancel()
    if serving.done():
        await serving
        return
    log.info("stopping: finishing the reply in progress")
    try:
        await asyncio.wait_for(serving, GRACE_SECONDS)
    except TimeoutError:
        log.warning("stopping: the reply in progress did not finish in time")


async def cancel_when(stop: asyncio.Event, receiver: asyncio.Task[None]) -> None:
    """Stop receiving as soon as a stop is asked for, so nothing is taken that won't be answered."""
    await stop.wait()
    receiver.cancel()


async def next_message[T](
    queue: asyncio.Queue[T], stop: asyncio.Event, receiver: asyncio.Task[None]
) -> T | None:
    """The next message, or None once a stop is asked for and nothing received is left. A receiver
    that failed raises its error here, so a surface that cannot connect stops the bot."""
    if stop.is_set():
        return None if queue.empty() else queue.get_nowait()
    getting = asyncio.ensure_future(queue.get())
    stopping = asyncio.ensure_future(stop.wait())
    await asyncio.wait({getting, stopping, receiver}, return_when=asyncio.FIRST_COMPLETED)
    stopping.cancel()
    if getting.done():
        return getting.result()
    getting.cancel()
    if receiver.done() and not receiver.cancelled():
        receiver.result()
    return None if queue.empty() else queue.get_nowait()
