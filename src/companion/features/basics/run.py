"""Ask what to call them and then their pronouns, and read their answers (J48)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from companion.core.extractor import Extractor
from companion.core.turn.address import KEY as ADDRESS_KEY
from companion.core.types import Speaker, Utterance
from companion.features.basics.logic import (
    ASK_EVERY,
    ASKED,
    ASKED_PRONOUNS,
    NAME_CAPTURE,
    NAME_SCHEMA,
    PRONOUN_CAPTURE,
    PRONOUN_SCHEMA,
    ask_name,
    ask_pronouns,
    asked_for_name,
    asked_for_pronouns,
    knows_name,
    name_belief,
    parse_name,
    parse_pronouns,
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


async def judge_pronouns(extractor: Extractor, asked: str, said: str) -> str | None:
    """The pronouns they gave in reply, or None."""
    judge = Judge(
        "basics",
        PRONOUN_CAPTURE,
        PRONOUN_SCHEMA,
        lambda data: parse_pronouns(data, said),
        timeout=TIMEOUT_SECONDS,
        unread="nothing set",
    )
    got = await ask(extractor, judge, f"COMPANION: {asked}\nUSER: {said}")
    return None if got is None else got.value


def _address_set(c: Conversation) -> bool:
    return bool((c.store.setting(c.rel, ADDRESS_KEY) or "").strip())


def basics_offer(m: Moment, found: object, so_far: Offered) -> Offer:
    """On a casual turn, at most once a day each: ask what to call them until memory knows, then
    which pronouns they use until the setting holds them. Never both on one turn."""
    del found
    if so_far["check-in"].lines:
        return Offer()
    c, t = m.c, m.t
    known = knows_name(m.beliefs)
    name_asked = c.store.decided_since(c.rel, ASKED, t.now - ASK_EVERY)
    note = ask_name(known=known, casual=m.casual, asked_recently=name_asked)
    if note is not None:
        return Offer((note,), (lambda: decide(c, t, ASKED),), asks=True)
    note = ask_pronouns(
        address_set=_address_set(c),
        name_known=known,
        casual=m.casual,
        name_asked=name_asked,
        asked_recently=c.store.decided_since(c.rel, ASKED_PRONOUNS, t.now - ASK_EVERY),
    )
    return (
        Offer()
        if note is None
        else Offer((note,), (lambda: decide(c, t, ASKED_PRONOUNS),), asks=True)
    )


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


async def capture_pronouns(c: Conversation, t: Turn) -> None:
    """When its last message asked their pronouns and nothing is set, read their answer and set how
    they want to be referred to, in their own words. Logged either way."""
    asked = next((u.text for u in reversed(t.prior) if u.speaker is Speaker.COMPANION), "")
    if c.judge is None or not asked_for_pronouns(asked) or _address_set(c):
        return
    pronouns = await judge_pronouns(c.judge, asked, t.text)
    reason = "basics: no pronouns in their answer"
    if pronouns is not None:
        c.store.set_setting(c.rel, ADDRESS_KEY, pronouns, t.now)
        reason = f"basics: set how to refer to them ({pronouns})"
    decide(c, t, "basics: pronoun capture", {"prompt": PRONOUN_CAPTURE.ref}, reason=reason)


async def capture(c: Conversation, t: Turn, said: Utterance, sent: str | None) -> None:
    """Once the turn is stored: the name, then the pronouns, from their answer."""
    await capture_name(c, t, said, sent)
    await capture_pronouns(c, t)


# What to call them and their pronouns: asked for on a casual turn until known, answers kept.
BASICS = Feature("name", note=basics_offer, after_turn=capture)
