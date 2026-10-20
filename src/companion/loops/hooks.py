"""Whether memory already states a basic fact (the J48 hook), with a time limit. A failure or a slow
model only means no shadow pick this turn."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from companion.core.extractor import Extractor
from companion.core.recall import SCHEMA, build_prompt, candidates, parse
from companion.core.spend import purpose
from companion.core.types import Belief
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
    try:
        with purpose("hook"):
            got = await asyncio.wait_for(
                extractor.extract(KNOWN.text, build_prompt(topic, labelled), SCHEMA),
                TIMEOUT_SECONDS,
            )
    except Exception as err:
        log.debug("basics check failed or was slow: %r", err)
        return None
    return parse(got.data, labelled)
