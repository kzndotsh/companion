"""A second model for calls the first refuses (2026-10-19).

The judges and the memory pass run on a model whose provider applies content moderation; on
stretches of explicit chat it refuses with a 403. Then the same call goes to a second model, and
the answer is marked so the floor never relies on it (ADR 0017): an age reading or an intimate
check from the fallback counts as unread. Anything other than a refusal is raised as before.
"""

from __future__ import annotations

import logging

import httpx

from companion.core.extractor import FALLBACK, Extraction, Extractor
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
