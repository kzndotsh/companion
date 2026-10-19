"""Ask the small model whether a reply added a joke on top of its reaction."""

from __future__ import annotations

import asyncio
import logging

from companion.core.extractor import Extractor
from companion.core.quip import SCHEMA, SYSTEM, build_prompt, parse
from companion.core.spend import purpose

TIMEOUT_SECONDS = 2.5
log = logging.getLogger("companion.quip")


async def judge_quip(
    extractor: Extractor, their_text: str, reply: str
) -> tuple[bool, str, str, float] | None:
    """Whether it added a joke, the model id, the prompt and the cost, or None if it could not be
    read in time."""
    prompt = build_prompt(their_text, reply)
    try:
        with purpose("quip"):
            result = await asyncio.wait_for(
                extractor.extract(SYSTEM, prompt, SCHEMA), TIMEOUT_SECONDS
            )
    except Exception as err:
        log.warning("quip check failed or timed out; the reply is kept: %r", err)
        return None
    added = parse(result.data)
    log.debug("quip check: added_joke=%s in %dms, $%.5f", added, result.latency_ms, result.cost_usd)
    return None if added is None else (added, result.model, prompt, result.cost_usd)
