"""Asking a small model the same question several times (`lib/vote.py`).

The fan-out every judged feature needs: the reads run at once, each failed call or unreadable
answer is a None read, and the cost of the reads that answered is summed. What a None read means
(no agreement, or try again later) is each feature's own rule.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import Json
from companion.lib.vote import READS

log = logging.getLogger("companion.reads")


@dataclass(frozen=True, slots=True)
class Reads[T]:
    values: tuple[T | None, ...]
    cost_usd: float
    model: str  # the model that answered, "" when none did

    @property
    def failed(self) -> bool:
        """Whether any read failed or could not be read."""
        return any(v is None for v in self.values)


async def read_times[T](  # noqa: PLR0913
    extractor: Extractor,
    system: str,
    user: str,
    schema: dict[str, Json],
    parse: Callable[[Json], T | None],
    *,
    spend: str,
    times: int = READS,
    timeout: float | None = None,
) -> Reads[T]:
    """The same question asked `times` times at once; with a timeout, a read slower than that many
    seconds is a None read."""

    async def one() -> tuple[T | None, float, str]:
        try:
            with purpose(spend):
                got = await asyncio.wait_for(extractor.extract(system, user, schema), timeout)
        except Exception as err:
            log.warning("%s read failed: %r", spend, err)
            return None, 0.0, ""
        return parse(got.data), got.cost_usd, got.model

    results = await asyncio.gather(*(one() for _ in range(times)))
    model = next((m for _, _, m in results if m), "")
    return Reads(tuple(v for v, _, _ in results), sum(c for _, c, _ in results), model)
