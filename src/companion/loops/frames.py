"""Ask the small model which frame a message is in. Any failure means no judgement."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import Sequence

from companion.core.extractor import Extractor
from companion.core.frames import SCHEMA, SYSTEM, Judgement, build_prompt, parse
from companion.core.spend import purpose
from companion.core.types import Utterance

TIMEOUT_SECONDS = 2.5
log = logging.getLogger("companion.frames")


def schema_hash() -> str:
    return hashlib.sha256(json.dumps(SCHEMA, sort_keys=True).encode()).hexdigest()


def inputs_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


async def judge_frame(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    try:
        with purpose("frame"):
            result = await asyncio.wait_for(
                extractor.extract(SYSTEM, prompt, SCHEMA), TIMEOUT_SECONDS
            )
    except Exception as err:
        log.warning("frame judgement failed or timed out; storing as real: %r", err)
        return None
    judged = parse(result.data)
    log.debug("frame judged %s in %dms, $%.5f", judged, result.latency_ms, result.cost_usd)
    return None if judged is None else (judged, result.model, prompt)
