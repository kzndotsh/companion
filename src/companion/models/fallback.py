"""Second models: for judge calls the first refuses, and for a reply the talker cannot give in time.

For judges (2026-10-19): the judges and the memory pass run on a model whose provider applies
content moderation; on stretches of explicit chat it refuses with a 403. Then the same call goes
to a second model, and the answer is marked so the floor never relies on it (ADR 0017): an age
reading or an intimate check from the fallback counts as unread. Anything other than a refusal
is raised as before.

For the talker (J21, 2026-10-19): a failed talker call used to mean the turn failed and they got
nothing, silently, and a stall could hold a reply for up to a minute. Now an error goes straight to
the fallback model, and a reply still missing after HEDGE_SECONDS asks the fallback too: whichever
answers first is sent and the other is cancelled. The reply carries the model that wrote it, so
flags and the ledger show it, and every check on a reply runs on it as on any other.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

import httpx

from companion.core.extractor import FALLBACK, Extraction, Extractor
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply, Talker
from companion.core.types import Json

REFUSED = 403
log = logging.getLogger("companion.fallback")


class RefusalFallback:
    def __init__(self, first: Extractor, second: Extractor) -> None:
        self._first, self._second = first, second

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        try:
            return await self._first.extract(system, user, schema)
        except httpx.HTTPStatusError as err:
            if err.response.status_code != REFUSED:
                raise
            log.warning("the first model refused (403); asking the fallback model")
        got = await self._second.extract(system, user, schema)
        return Extraction(got.data, got.model + FALLBACK, got.cost_usd, got.latency_ms)


HEDGE_SECONDS = 10.0


async def _cancel(*tasks: asyncio.Task[Reply]) -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task


class TalkerFallback:
    def __init__(
        self, first: Talker, fallback: Talker, hedge_seconds: float = HEDGE_SECONDS
    ) -> None:
        self._first, self._fallback, self._hedge = first, fallback, hedge_seconds

    async def reply(self, request: TalkerRequest) -> Reply:
        first = asyncio.ensure_future(self._first.reply(request))
        try:
            done, _ = await asyncio.wait({first}, timeout=self._hedge)
            if done:
                error = first.exception()
                if error is None:
                    return first.result()
                log.warning("the talker failed (%r); the fallback model answers", error)
                return await self._fallback.reply(request)
            log.warning("no reply after %.0fs; asking the fallback model too", self._hedge)
            second = asyncio.ensure_future(self._fallback.reply(request))
            return await _first_good(first, second)
        except asyncio.CancelledError:
            await _cancel(first)
            raise


async def _first_good(first: asyncio.Task[Reply], second: asyncio.Task[Reply]) -> Reply:
    """Whichever succeeds first; the other is cancelled. Raises only when both fail."""
    pending = {first, second}
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task.exception() is None:
                    who = "the fallback" if task is second else "the talker"
                    log.info("%s answered first", who)
                    return task.result()
        raise first.exception() or RuntimeError("both models failed")
    finally:
        await _cancel(*pending)
