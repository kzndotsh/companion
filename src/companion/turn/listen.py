"""The listen stage of a turn: a reaction instead of a reply, and the listening judge's read.

The listening judge asks the small model how serious a message is and what the person is doing."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING

from companion.core.crisis import cue_words
from companion.core.extractor import StructuredModel
from companion.core.turn.context import build_prompt
from companion.core.turn.listening import PROMPT, SCHEMA, ListeningRead, parse
from companion.core.turn.reply import Reaction
from companion.core.types import Frame, Utterance
from companion.kit.ask import Judge, ask
from companion.kit.current import Heard, Turn
from companion.turn.reactions import react_instead
from companion.turn.values import Listened, stop

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

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


async def hear_them(c: Runtime, t: Turn, in_scene: Frame) -> Heard | None:
    """How serious the message is and what they are doing. Not asked in a scene."""
    if c.judge is None or not c.listen or in_scene is not Frame.REAL:
        return None
    return await judge_listening(c.judge, t.prior, t.text)


async def _reaction_instead(c: Runtime, t: Turn) -> Reaction | None:
    """With the crisis path on, a message with a crisis cue word always gets a reply (ADR 0022)."""
    cue = c.crisis == "on" and bool(cue_words(t.text))
    return await react_instead(c, t, crisis_cue=cue)


async def listen(c: Runtime, t: Turn, in_scene: Frame) -> Listened:
    """The listen stage: whether a reaction answers instead of a reply, and if not, what the
    listening judge heard. The two run side by side; a failure stops both and goes on up."""
    listening = asyncio.ensure_future(hear_them(c, t, in_scene))
    try:
        reaction = await _reaction_instead(c, t)
        if reaction is not None:
            await stop(listening)
            return Listened(reaction, None)
        return Listened(None, await listening)
    except BaseException:
        await stop(listening)
        raise
