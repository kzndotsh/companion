"""Ask the small model whether a reply on a held turn is sexual (ADR 0017)."""

from __future__ import annotations

import asyncio
import logging

from companion.core.extractor import Extractor
from companion.core.floor import INTIMATE_CHECK, INTIMATE_SCHEMA, parse_intimate
from companion.core.spend import purpose

TIMEOUT_SECONDS = 3.0
log = logging.getLogger("companion.floor")


async def judge_intimate(extractor: Extractor, reply: str) -> bool | None:
    """Whether the reply is sexual, or None when it could not be read in time."""
    try:
        with purpose("floor"):
            result = await asyncio.wait_for(
                extractor.extract(INTIMATE_CHECK.text, f"COMPANION: {reply}", INTIMATE_SCHEMA),
                TIMEOUT_SECONDS,
            )
    except Exception as err:
        log.warning("intimate check failed or timed out; treated as intimate: %r", err)
        return None
    return parse_intimate(result.data)
