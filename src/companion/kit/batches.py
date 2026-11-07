"""Labelling memories in batches: the loop two label steps share (the memory map, the view kinds).
Each pass takes up to `batches` batches of what has no label yet; a batch that cannot be read stops
the loop and is tried again next pass, so a memory is never labelled from a half answer."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

log = logging.getLogger("companion.batches")


@dataclass(frozen=True, slots=True)
class Swept:
    labelled: int = 0
    left: int = 0
    cost_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class Batch:
    """What one batch did: how many it labelled, what it cost, and whether to stop the loop."""

    labelled: int = 0
    cost_usd: float = 0.0
    stop: bool = False


async def label_in_batches[T](
    what: str,
    *,
    batches: int,
    todo: Callable[[], Sequence[T]],
    label: Callable[[Sequence[T]], Awaitable[Batch]],
    left: Callable[[], int],
) -> Swept:
    """Up to `batches` batches: `todo` is the next batch (empty ends the loop), `label` reads and
    keeps it, `left` counts what still has no label. Logged as `what`."""
    done = 0
    cost = 0.0
    for _ in range(batches):
        batch = todo()
        if not batch:
            break
        result = await label(batch)
        cost += result.cost_usd
        done += result.labelled
        if result.stop:
            break
    remaining = left()
    log.debug("%s: %d labelled, %d left, $%.4f", what, done, remaining, cost)
    return Swept(done, remaining, cost)
