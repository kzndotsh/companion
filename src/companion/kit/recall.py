"""The look-up when they ask the companion to remember, with a time limit. A failure or a slow
model only means nothing is looked up; the reply goes out as it would have."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from companion.core.clock import local_zone
from companion.core.extractor import StructuredModel
from companion.core.freshness import when_phrase
from companion.core.recall import PROMPT, SCHEMA, build_prompt, candidates, parse
from companion.core.types import Belief, BeliefId
from companion.kit.ask import Judge, ask

log = logging.getLogger("companion.recall")
TIMEOUT_SECONDS = 3.0


@dataclass(frozen=True, slots=True)
class Recalled:
    topic: str
    picked: tuple[Belief, ...]
    searched: int
    model: str


async def look_up(
    extractor: StructuredModel,
    beliefs: Sequence[Belief],
    topic: str,
    *,
    said: Mapping[BeliefId, datetime] | None = None,
    now: datetime | None = None,
) -> Recalled | None:
    """The beliefs that bear on what they asked it to remember, or None if the look-up failed. With
    `said` (when each was last said) and `now`, each line carries how long ago."""
    labelled = candidates(beliefs)
    when = (
        {k: when_phrase(said.get(b.id, b.valid_from), now) for k, b in labelled.items()}
        if said is not None and now is not None
        else None
    )
    today = f"{now.astimezone(local_zone()):%A %d %B %Y}" if now is not None else ""
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
    got = await ask(extractor, judge, build_prompt(topic, labelled, when, today))
    if got is None:
        return None
    return Recalled(topic, tuple(got.value), len(labelled), got.model)
