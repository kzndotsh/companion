"""Ask the small model whether a message deserves a reaction as well as a reply."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from companion.core.ack import build_prompt
from companion.core.extractor import Extractor
from companion.core.react import SCHEMA, SYSTEM, Judgement, parse
from companion.core.types import Utterance

TIMEOUT_SECONDS = 2.5
log = logging.getLogger("companion.react")


async def judge_reaction(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    try:
        result = await asyncio.wait_for(extractor.extract(SYSTEM, prompt, SCHEMA), TIMEOUT_SECONDS)
    except Exception:
        log.warning("reaction judgement failed or timed out; no reaction")
        return None
    judged = parse(result.data)
    return None if judged is None else (judged, result.model, prompt)
