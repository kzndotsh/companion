"""The look-up when they ask the companion to remember, with a time limit. A failure or a slow
model only means nothing is looked up; the reply goes out as it would have."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.extractor import Extractor
from companion.core.recall import PROMPT, SCHEMA, build_prompt, candidates, parse
from companion.core.types import Belief
from companion.loops.ask import Judge, ask

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
    judge = Judge(
        "recall",
        PROMPT,
        SCHEMA,
        lambda data: parse(data, labelled),
        timeout=TIMEOUT_SECONDS,
        unread="nothing added",
    )
    got = await ask(extractor, judge, build_prompt(topic, labelled))
    if got is None:
        return None
    return Recalled(topic, tuple(got.value), len(labelled), got.model)
