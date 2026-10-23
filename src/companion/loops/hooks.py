"""Whether memory already states a basic fact (the J48 hook), with a time limit. A failure or a slow
model only means no shadow pick this turn."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from companion.core.extractor import Extractor
from companion.core.recall import SCHEMA, build_prompt, candidates, parse
from companion.core.types import Belief
from companion.loops.ask import Judge, ask
from companion.prompts import get

log = logging.getLogger("companion.hooks")
KNOWN = get("system/basics-known")
TIMEOUT_SECONDS = 5.0


async def stated(
    extractor: Extractor, beliefs: Sequence[Belief], topic: str
) -> list[Belief] | None:
    """The memories that state the fact outright, or None when the call failed or was slow."""
    labelled = candidates(beliefs)
    if not labelled:
        return []
    judge = Judge(
        "hook",
        KNOWN,
        SCHEMA,
        lambda data: parse(data, labelled),
        timeout=TIMEOUT_SECONDS,
        unread="no shadow pick this turn",
    )
    got = await ask(extractor, judge, build_prompt(topic, labelled))
    return None if got is None else got.value
