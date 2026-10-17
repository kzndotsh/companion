"""Ask the small model how serious a message is and what the person is doing."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from companion.core.ack import build_prompt
from companion.core.extractor import Extractor
from companion.core.listening import SCHEMA, SYSTEM, Judgement, parse
from companion.core.spend import purpose
from companion.core.types import Utterance

TIMEOUT_SECONDS = 2.5
log = logging.getLogger("companion.listen")


async def judge_listening(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The labels, the model id and the prompt, or None if they could not be made in time. A
    missing label only means no note, so a slow or failing judge never delays the reply for long."""
    prompt = build_prompt(history, text)
    try:
        with purpose("listen"):
            result = await asyncio.wait_for(
                extractor.extract(SYSTEM, prompt, SCHEMA), TIMEOUT_SECONDS
            )
    except Exception as err:
        log.warning("listening judgement failed or timed out; no note: %r", err)
        return None
    judged = parse(result.data)
    log.debug("listening judged %s in %dms, $%.5f", judged, result.latency_ms, result.cost_usd)
    return None if judged is None else (judged, result.model, prompt)
