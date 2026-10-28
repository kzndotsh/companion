"""What is happening with them now (ADR 0024): beside each real turn, a small model labels their
message (something coming, leaving, back, done); before a reply, while something they said is
coming is still open, one line after the history says so (`COMPANION_NOW`; in shadow it is logged,
not sent). Nudges read the same labels for a time away.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companion.core.card import Card
from companion.core.recheck import SERIOUS
from companion.core.turn.now import (
    KEY,
    LOOKBACK,
    NOTE,
    PROMPT,
    SCHEMA,
    Phase,
    from_decisions,
    parse,
    reader_input,
    soon_note,
)
from companion.core.types import Frame, Json
from companion.loops.ask import Judge, ask
from companion.loops.current import Heard, Turn, decide
from companion.loops.features import Feature, Moment, Offer, Offered

if TYPE_CHECKING:
    from companion.loops.runtime import Runtime

READER = Judge("now", PROMPT, SCHEMA, parse, timeout=8.0, unread="no label for this message")
SENT = "now: told it what they said is still coming"
SHADOW = "now: would tell it what they said is still coming (shadow, not sent)"


async def read_now(c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None, card: Card) -> None:
    """Label their message once the reply is out, on any real turn that is not serious: "gotta run"
    and "food's here" are exactly the messages to read. Nothing is logged for `none`. Runs while the
    note or reaching out is on, since nudges read the labels too."""
    del card
    serious = heard is None or heard[0].severity >= SERIOUS
    wanted = c.now != "off" or c.initiative
    if not wanted or c.judge is None or serious or in_scene is not Frame.REAL:
        return
    got = await ask(c.judge, READER, reader_input(t.prior, t.text))
    if got is None or got.value.phase is Phase.NONE:
        return
    label = got.value
    detail: dict[str, Json] = {
        "phase": label.phase.value,
        "what": label.what,
        "minutes": label.minutes,
        "said": t.text,
        "model": got.model,
        "prompt": got.ref,
    }
    decide(c, t, KEY, detail, reason=f"{KEY}: {label.phase.value} {label.what}".rstrip())


def now_note(m: Moment, found: object, so_far: Offered) -> Offer:
    """While something they said is coming is still open, one line after the history that says so
    and how long ago, outside a scene and the crisis path. Logged once the turn is stored."""
    del found, so_far
    c, t = m.c, m.t
    if c.now == "off" or m.in_scene is not Frame.REAL or m.risk:
        return Offer()
    line = soon_note(
        from_decisions(c.store.decisions_with_key(c.rel, KEY, t.now - LOOKBACK)), t.now
    )
    if line is None:
        return Offer()
    detail: dict[str, Json] = {"note": line, "prompt": NOTE.ref}
    if c.now == "shadow":
        return Offer(after=(lambda: decide(c, t, SHADOW, detail),))
    return Offer(tail=(line,), after=(lambda: decide(c, t, SENT, detail),))


# What they said is coming, kept until it happens (ADR 0024).
NOW = Feature("now", note=now_note, shadow=read_now)
