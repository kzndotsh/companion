"""Ask whether a small topic has run its course, with a time limit. A failure means no note."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from companion.core.extractor import Extractor, from_fallback
from companion.core.spend import purpose
from companion.core.topics import JUDGE, SCHEMA, judge_prompt, parse
from companion.core.types import Utterance

TIMEOUT_SECONDS = 3.0
log = logging.getLogger("companion.topics")


async def judge_spent(extractor: Extractor, prior: Sequence[Utterance], said: str) -> bool:
    try:
        with purpose("topics"):
            result = await asyncio.wait_for(
                extractor.extract(JUDGE.text, judge_prompt(prior, said), SCHEMA), TIMEOUT_SECONDS
            )
    except Exception as err:
        log.warning("topic judge failed or timed out; no note: %r", err)
        return False
    return parse(result.data) and not from_fallback(result.model)
