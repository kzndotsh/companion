"""Ask the small model how serious a message is and what the person is doing."""

from __future__ import annotations

from collections.abc import Sequence

from companion.core.extractor import StructuredModel
from companion.core.turn.ack import build_prompt
from companion.core.turn.listening import PROMPT, SCHEMA, ListeningRead, parse
from companion.core.types import Utterance
from companion.kit.ask import Judge, ask

TIMEOUT_SECONDS = 3.0
# Its answers took 1.5 s at the median and 2.0 s at the 90th percentile, and about one try in
# eleven ran past 2.5 s and was thrown away (logs to 2026-10-28). A second try now starts at 1.8 s
# while the slow one keeps running, and the first answer wins.
HEDGE_SECONDS = 1.8
LISTEN = Judge(
    "listen",
    PROMPT,
    SCHEMA,
    parse,
    timeout=TIMEOUT_SECONDS,
    unread="no note, no recall and no routing this turn",
    attempts=2,  # a missed reading costs a recall, a note and a route, so one retry is worth it
    hedge=HEDGE_SECONDS,
)


async def judge_listening(
    extractor: StructuredModel, history: Sequence[Utterance], text: str
) -> tuple[ListeningRead, str, str] | None:
    """The labels, the model id and the prompt, or None if two tries could not make them in time."""
    prompt = build_prompt(history, text)
    got = await ask(extractor, LISTEN, prompt)
    return None if got is None else (got.value, got.model, prompt)
