"""Ask the small model how serious a message is and what the person is doing."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.ack import build_prompt
from companion.core.extractor import Extractor
from companion.core.listening import PROMPT, SCHEMA, Judgement, parse
from companion.core.types import Utterance
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 2.5
LISTEN = Judge(
    "listen",
    PROMPT,
    SCHEMA,
    parse,
    timeout=TIMEOUT_SECONDS,
    unread="no note, no recall and no routing this turn",
    attempts=2,  # a missed reading costs a recall, a note and a route, so one retry is worth it
)


async def judge_listening(
    extractor: Extractor, history: Sequence[Utterance], text: str
) -> tuple[Judgement, str, str] | None:
    """The labels, the model id and the prompt, or None if two tries could not make them in time."""
    prompt = build_prompt(history, text)
    got = await ask(extractor, LISTEN, prompt)
    return None if got is None else (got.value, got.model, prompt)
