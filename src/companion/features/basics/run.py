"""Read their answer when the companion asked what to call them (J48)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from companion.core.extractor import Extractor
from companion.core.types import Speaker, Utterance
from companion.features.basics.logic import (
    ASK_EVERY,
    ASKED,
    NAME_CAPTURE,
    NAME_SCHEMA,
    ask_name,
    asked_for_name,
    knows_name,
    name_belief,
    parse_name,
)
from companion.loops.current import Turn, decide
from companion.loops.features import Feature, Moment, Offer, Offered

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation
from companion.loops.ask import Judge, ask

TIMEOUT_SECONDS = 3.0


async def judge_name(extractor: Extractor, asked: str, said: str) -> str | None:
    """The name they gave in reply, or None."""
    judge = Judge(
        "basics",
        NAME_CAPTURE,
        NAME_SCHEMA,
        lambda data: parse_name(data, said),
        timeout=TIMEOUT_SECONDS,
        unread="no name stored",
    )
    got = await ask(extractor, judge, f"COMPANION: {asked}\nUSER: {said}")
    return None if got is None else got.value


def name_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """Offer to ask what to call them on a casual turn, at most once a day, until memory knows."""
    del found
    if so_far["check-in"].lines:
        return Offer()
    c, t = m.c, m.t
    note = ask_name(
        known=knows_name(m.beliefs),
        casual=m.casual,
        asked_recently=c.store.decided_since(c.rel, ASKED, t.now - ASK_EVERY),
    )
    return Offer() if note is None else Offer((note,), (lambda: decide(c, t, ASKED),))


async def capture_name(c: Conversation, t: Turn, said: Utterance, sent: str | None) -> None:
    """When its last message asked what to call them, read their answer and remember the name,
    quoting their own words. Logged either way."""
    del sent
    asked = next((u.text for u in reversed(t.prior) if u.speaker is Speaker.COMPANION), "")
    if c.judge is None or not asked_for_name(asked):
        return
    if knows_name(c.store.user_beliefs(c.rel)):
        return
    name = await judge_name(c.judge, asked, t.text)
    reason = "basics: no name in their answer"
    if name is not None:
        c.store.insert_belief(name_belief(said, name, uuid.uuid4().hex, t.now))
        reason = f"basics: remembered what to call them ({name})"
    decide(c, t, "basics: name capture", {"prompt": NAME_CAPTURE.ref}, reason=reason)


# What to call them: asked for on a casual turn until memory knows, and their answer remembered.
BASICS = Feature("name", note=name_offer, after_turn=capture_name)
