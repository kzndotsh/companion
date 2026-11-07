"""Ask the small model which frame a message is in. Any failure means no judgement."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.extractor import StructuredModel
from companion.core.frames import CONTEXT_MESSAGES, PROMPT, SCHEMA, Judgement, parse
from companion.core.turn.context import Scored, conversation_prompt
from companion.core.types import Utterance
from companion.kit.ask import Judge, ask

TIMEOUT_SECONDS = 2.5
FRAME = Judge("frame", PROMPT, SCHEMA, parse, timeout=TIMEOUT_SECONDS, unread="storing as real")


async def judge_frame(
    extractor: StructuredModel, history: Sequence[Utterance], text: str
) -> Scored[Judgement] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = conversation_prompt(history, text, last=CONTEXT_MESSAGES)
    got = await ask(extractor, FRAME, prompt)
    return None if got is None else Scored(got.value, got.model, prompt)
