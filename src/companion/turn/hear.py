"""The listen stage of a turn: a reaction instead of a reply, and the listening judge's read."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from companion.core.turn.ack import PROMPT as ACK_PROMPT
from companion.core.turn.ack import (
    REACT_THRESHOLD,
    Reaction,
    inputs_hash,
    is_candidate,
    reaction_for,
    render_reason,
    schema_hash,
)
from companion.core.turn.listening import SERIOUS
from companion.core.types import (
    Frame,
    Speaker,
)
from companion.features.crisis.logic import cue_words
from companion.loops.current import Heard, Turn, decide, mark
from companion.store.sqlite.decisions import REACTED
from companion.turn.ack import judge
from companion.turn.listen import judge_listening
from companion.turn.values import Listened, stop

if TYPE_CHECKING:
    from companion.loops.runtime import Runtime

log = logging.getLogger("companion.turn")


async def ack_reaction(c: Runtime, t: Turn) -> Reaction | None:
    """A reaction if this short message only acknowledges. Logs every judgement it makes. With the
    crisis path on, a message with a crisis cue word always gets a reply (ADR 0022)."""
    if c.judge is None or not is_candidate(t.text, t.prior, after_serious=_after_serious(c, t)):
        mark(t, "ack judge skipped: not a candidate for a reaction")
        return None
    if c.crisis == "on" and cue_words(t.text):
        mark(t, "ack judge skipped: a crisis cue word, it gets a reply")
        return None
    outcome = await judge(c.judge, t.prior, t.text)
    if outcome is None:
        mark(t, "ack judge gave no answer; replying")
        return None
    judged, model, prompt = outcome
    reaction = reaction_for(judged)
    mark(
        t, f"ack judged {judged.kind} {judged.confidence:.2f} -> {'react' if reaction else 'reply'}"
    )
    decide(
        c,
        t,
        REACTED if reaction is not None else "ack: replied",
        {
            "scorer": model,
            "prompt": ACK_PROMPT.ref,
            "schema_hash": schema_hash(),
            "inputs_hash": inputs_hash(prompt),
            "scores": {"kind": judged.kind, "confidence": judged.confidence},
            "threshold": REACT_THRESHOLD,
        },
        reason=render_reason(judged, reaction is not None),
    )
    return reaction


def _after_serious(c: Runtime, t: Turn) -> bool:
    """Whether the listening judge found their previous message serious (severity 2 or more)."""
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs:
        return False
    for d in c.store.decisions_for_turn(c.rel, theirs[-1].turn_id):
        labels = d.detail.get("labels") if d.detail else None
        severity = labels.get("severity") if isinstance(labels, dict) else None
        if isinstance(severity, int) and not isinstance(severity, bool) and severity >= SERIOUS:
            return True
    return False


async def hear_them(c: Runtime, t: Turn, in_scene: Frame) -> Heard | None:
    """How serious the message is and what they are doing. Not asked in a scene."""
    if c.judge is None or not c.listen or in_scene is not Frame.REAL:
        return None
    return await judge_listening(c.judge, t.prior, t.text)


async def listen(c: Runtime, t: Turn, in_scene: Frame) -> Listened:
    """The listen stage: whether a reaction answers instead of a reply, and if not, what the
    listening judge heard. The two run side by side; a failure stops both and goes on up."""
    listening = asyncio.ensure_future(hear_them(c, t, in_scene))
    try:
        reaction = await ack_reaction(c, t)
        if reaction is not None:
            await stop(listening)
            return Listened(reaction, None)
        return Listened(None, await listening)
    except BaseException:
        await stop(listening)
        raise
