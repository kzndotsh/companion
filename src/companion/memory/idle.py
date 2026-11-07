"""The memory pass the bot runs once the chat has been quiet for a while: every message restarts
the wait, and a pass that finds the day's spend at the cap, or no connection, leaves the reading for
the next message."""

from __future__ import annotations

import asyncio
import logging

import httpx

from companion.core.clock import utc_now
from companion.core.extractor import StructuredModel
from companion.core.types import RelationshipId
from companion.kit.spendcap import over_cap
from companion.lib import retry
from companion.memory.memory_pass import PassOptions, memory_pass
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.memory")
PASS_IDLE_SECONDS = 90
PASS_RETRY_DELAYS = (30.0, 120.0)  # a dropped connection, not a model error


class IdlePass:
    """Runs one memory pass `PASS_IDLE_SECONDS` after the last `schedule`."""

    def __init__(
        self,
        store: Store,
        judges: StructuredModel,
        rel: RelationshipId,
        options: PassOptions,
        daily_cap: float | None,
    ) -> None:
        self._store, self._judges, self._rel = store, judges, rel
        self._options, self._cap = options, daily_cap
        self._pending: asyncio.Task[None] | None = None

    def schedule(self) -> None:
        """Start the wait again: a pass already waiting is dropped."""
        self.cancel()
        self._pending = asyncio.create_task(self._after_idle())

    def cancel(self) -> None:
        if self._pending is not None:
            self._pending.cancel()

    async def _after_idle(self) -> None:
        await asyncio.sleep(PASS_IDLE_SECONDS)
        log.debug("idle for %ds; reading what has not been read", PASS_IDLE_SECONDS)
        if over_cap(self._store, self._rel, self._cap, utc_now()) is not None:
            log.warning("daily spend cap reached; no memory pass")
            return
        try:
            result = await retry.retry_on_network_error(
                lambda: memory_pass(self._store, self._judges, self._rel, self._options),
                PASS_RETRY_DELAYS,
                "memory pass",
            )
        except httpx.TransportError as err:
            log.warning(
                "memory pass could not reach the model (%s); it runs after their next message",
                type(err).__name__,
            )
            return
        except Exception:
            log.exception("the memory pass failed, will retry")
            return
        if result.ran:
            log.info("memory pass: %s", result.summary())
