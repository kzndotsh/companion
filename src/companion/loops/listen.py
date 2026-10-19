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
ATTEMPTS = 2  # a missed reading costs a recall, a note and a route, so one retry is worth it
log = logging.getLogger("companion.listen")


async def judge_listening(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The labels, the model id and the prompt, or None if two tries could not make them in time.
    A missing reading means no note, no recall and no routing, so it is tried once more."""
    prompt = build_prompt(history, text)
    result = None
    for attempt in range(ATTEMPTS):
        try:
            with purpose("listen"):
                result = await asyncio.wait_for(
                    extractor.extract(SYSTEM, prompt, SCHEMA), TIMEOUT_SECONDS
                )
            break
        except Exception as err:
            log.warning("listening judgement failed or timed out (try %d): %r", attempt + 1, err)
    if result is None:
        return None
    judged = parse(result.data)
    log.debug("listening judged %s in %dms, $%.5f", judged, result.latency_ms, result.cost_usd)
    return None if judged is None else (judged, result.model, prompt)
