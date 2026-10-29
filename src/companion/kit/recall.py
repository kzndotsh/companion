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
from companion.core.recall import (
    ASKED_SENSITIVITY,
    PROMPT,
    SCHEMA,
    build_prompt,
    candidates,
    parse,
)
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


@dataclass(frozen=True, slots=True)
class Context:
    """The turn around an ask: when each belief was last said, the time, and the last messages of
    the conversation, each starting "they:" or "you:"."""

    said: Mapping[BeliefId, datetime]
    now: datetime
    recent: Sequence[str] = ()


async def look_up(
    extractor: StructuredModel,
    beliefs: Sequence[Belief],
    topic: str,
    context: Context | None = None,
) -> Recalled | None:
    """The beliefs that bear on what they asked it to remember, or None if the look-up failed. They
    asked, so any stated belief may be found; a caller that must not reach sensitive ones leaves
    them out of `beliefs`. With `context`, each line carries how long ago it was said and the judge
    reads the conversation too."""
    labelled = candidates(beliefs, ASKED_SENSITIVITY)
    when = None
    if context is not None:
        said, now = context.said, context.now
        when = {k: when_phrase(said.get(b.id, b.valid_from), now) for k, b in labelled.items()}
    today = f"{context.now.astimezone(local_zone()):%A %d %B %Y}" if context is not None else ""
    recent = context.recent if context is not None else ()
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
    got = await ask(extractor, judge, build_prompt(topic, labelled, when, today, recent))
    if got is None:
        return None
    return Recalled(topic, tuple(got.value), len(labelled), got.model)
