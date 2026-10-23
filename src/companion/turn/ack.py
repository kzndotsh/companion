"""Ask the small model whether a short message needs a reply. Any failure means reply."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.extractor import Extractor
from companion.core.turn.ack import PROMPT, SCHEMA, Judgement, build_prompt, parse
from companion.core.types import Utterance
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 2.0
ACK = Judge("ack", PROMPT, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="replying normally")


async def judge(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    got = await ask(extractor, ACK, prompt)
    return None if got is None else (got.value, got.model, prompt)
