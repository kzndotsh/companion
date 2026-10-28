"""The crisis path's place in the turn (ADR 0022): a literal risk read ends a scene for the turn, a
reply that names means or methods is drawn once more, and on an urgent turn code's own fixed
message with the crisis line goes after the reply. In shadow each only logs what it would do."""

from __future__ import annotations

import dataclasses
import uuid
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TYPE_CHECKING

from companion.core.crisis import CrisisLevel, Reading
from companion.core.talker import Reply
from companion.core.turn.ack import ReactAndReply, ThenSend
from companion.core.types import Frame, Speaker, Utterance, UtteranceId
from companion.features.crisis.logic import line_message, method_words
from companion.features.crisis.run import (
    LINE_NOT_REPEATED,
    LINE_SENT,
    METHOD,
    NAME,
    SCENE,
    reading_in,
)
from companion.kit.current import Turn, decide, mark
from companion.kit.features import Lookups
from companion.turn.values import Routed

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime
    from companion.turn.persist import TheirMessage

LINE_EVERY = timedelta(hours=1)  # the same fixed message is not sent twice inside this


def reading_of(looked: Lookups) -> Reading | None:
    return reading_in(looked.found.get(NAME))


def off_scene(c: Runtime, t: Turn, routed: Routed, reading: Reading | None) -> Routed:
    """The route with this turn's reading. A literal risk read in a scene, or on the roleplay
    talker, goes to the everyday talker as a real turn when on; in shadow that is only logged."""
    routed = dataclasses.replace(routed, crisis=reading)
    if reading is None or not reading.risk:
        return routed
    if routed.talker is not c.roleplay_talker and routed.in_scene is Frame.REAL:
        return routed
    if not reading.acts:
        decide(
            c,
            t,
            SCENE,
            {"acted": False},
            reason="crisis: would end the scene for this turn and answer with the everyday talker",
        )
        return routed
    decide(
        c,
        t,
        SCENE,
        {"acted": True},
        reason="crisis: a literal risk read ends the scene for this turn, the everyday talker"
        " answers",
    )
    return dataclasses.replace(routed, talker=c.talker, in_scene=Frame.REAL)


async def method_checked(
    c: Runtime,
    t: Turn,
    draw: Callable[[], Awaitable[Reply]],
    reply: Reply,
    reading: Reading | None,
) -> Reply:
    """On a concern or urgent turn, a reply that names means or methods in a how-to way is drawn
    once more, and the redraw goes out. Nothing is edited; the first is kept in the decision."""
    if reading is None or not reading.risk:
        return reply
    found = method_words(reply.text, t.text)
    if not found:
        return reply
    named = ", ".join(found)
    if not reading.acts:
        decide(
            c,
            t,
            METHOD,
            {"found": list(found), "acted": False},
            reason=f"crisis: would redraw a reply naming means or methods ({named})",
        )
        return reply
    again = await draw()
    mark(t, f"crisis redraw: {again.model} {len(again.text.split())} words")
    still = method_words(again.text, t.text)
    decide(
        c,
        t,
        METHOD,
        {"found": list(found), "discarded": reply.text, "still": list(still), "acted": True},
        reason=f"crisis: redrew a reply naming means or methods ({named})",
    )
    return again if again.text else reply


def then_line(
    keep: TheirMessage, reading: Reading | None, out: str | ReactAndReply, reply: Reply
) -> str | ReactAndReply | ThenSend:
    """On an urgent turn with the path on, the fixed crisis-line message after the reply: from the
    character's `## Crisis message` section, else the default. Stored as its own message and
    logged; not sent again inside LINE_EVERY."""
    if reading is None or reading.level is not CrisisLevel.URGENT or not reading.acts:
        return out
    c, t = keep.c, keep.t
    if c.store.decided_since(c.rel, LINE_SENT, t.now - LINE_EVERY):
        decide(c, t, LINE_NOT_REPEATED, reason="crisis: the line went out within the hour")
        return out
    text, source = line_message(c.serious_message)
    at = t.now + timedelta(milliseconds=max(reply.latency_ms, 1) + 1)
    said = Utterance(
        UtteranceId(uuid.uuid4().hex),
        c.rel,
        t.session,
        t.turn,
        Speaker.COMPANION,
        text,
        Frame.REAL,
        keep.platform,
        at,
    )
    c.store.append_utterance(said)
    decide(c, t, LINE_SENT, {"source": source}, reason=f"crisis: line sent, from {source}", at=at)
    return ThenSend(out, text)
