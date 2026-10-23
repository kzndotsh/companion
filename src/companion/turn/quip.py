"""Ask the small model whether a reply added a joke on top of its reaction."""

from __future__ import annotations

from companion.core.extractor import Extractor
from companion.core.turn.quip import PROMPT, SCHEMA, build_prompt, parse
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 2.5


QUIP = Judge("quip", PROMPT, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="the reply is kept")


async def judge_quip(
    extractor: Extractor, their_text: str, reply: str
) -> tuple[bool, str, str, float] | None:
    """Whether it added a joke, the model id, the prompt and the cost, or None if it could not be
    read in time."""
    prompt = build_prompt(their_text, reply)
    got = await ask(extractor, QUIP, prompt)
    return None if got is None else (got.value, got.model, prompt, got.cost_usd)
