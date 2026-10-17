"""Ask the small model whether a short message needs a reply. Any failure means reply."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from companion.core.ack import SCHEMA, SYSTEM, Judgement, build_prompt, parse
from companion.core.extractor import Extractor
from companion.core.spend import purpose
from companion.core.types import Utterance

TIMEOUT_SECONDS = 2.0
log = logging.getLogger("companion.ack")


async def judge(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    try:
        with purpose("ack"):
            result = await asyncio.wait_for(
                extractor.extract(SYSTEM, prompt, SCHEMA), TIMEOUT_SECONDS
            )
    except Exception:
        log.warning("ack judgement failed or timed out; replying normally")
        return None
    judged = parse(result.data)
    return None if judged is None else (judged, result.model, prompt)
