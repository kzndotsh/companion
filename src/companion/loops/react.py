"""Ask the small model whether a message deserves a reaction as well as a reply."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.ack import build_prompt
from companion.core.extractor import Extractor
from companion.core.react import PROMPT, SCHEMA, Judgement, parse
from companion.core.types import Utterance
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 2.5
REACT = Judge("reaction", PROMPT, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="no reaction")


async def judge_reaction(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    got = await ask(extractor, REACT, prompt)
    return None if got is None else (got.value, got.model, prompt)
