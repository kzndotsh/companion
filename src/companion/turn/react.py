"""Ask the small model whether a message deserves a reaction as well as a reply."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.extractor import StructuredModel
from companion.core.turn.ack import build_prompt
from companion.core.turn.react import PROMPT, SCHEMA, ToneRead, parse
from companion.core.types import Utterance
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 2.5
REACT = Judge("reaction", PROMPT, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="no reaction")


async def judge_reaction(
    extractor: StructuredModel, history: Sequence[Utterance], text: str
) -> tuple[ToneRead, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    got = await ask(extractor, REACT, prompt)
    return None if got is None else (got.value, got.model, prompt)
