"""The look-up when they ask the companion to remember, with a time limit. A failure or a slow
model only means nothing is looked up; the reply goes out as it would have."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.extractor import Extractor
from companion.core.recall import SCHEMA, SYSTEM, build_prompt, candidates, parse
from companion.core.spend import purpose
from companion.core.types import Belief

log = logging.getLogger("companion.recall")
TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True, slots=True)
class Recalled:
    topic: str
    picked: tuple[Belief, ...]
    searched: int
    model: str


async def look_up(extractor: Extractor, beliefs: Sequence[Belief], topic: str) -> Recalled | None:
    """The beliefs that bear on what they asked it to remember, or None if the look-up failed."""
    labelled = candidates(beliefs)
    if not labelled:
        return Recalled(topic, (), 0, "")
    try:
        with purpose("recall"):
            result = await asyncio.wait_for(
                extractor.extract(SYSTEM, build_prompt(topic, labelled), SCHEMA), TIMEOUT_SECONDS
            )
    except Exception as err:
        log.warning("recall look-up failed or timed out; nothing added: %r", err)
        return None
    picked = parse(result.data, labelled)
    log.debug(
        "recall %r: %d of %d picked, $%.5f", topic, len(picked), len(labelled), result.cost_usd
    )
    return Recalled(topic, tuple(picked), len(labelled), result.model)
