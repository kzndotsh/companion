"""Whole turns against judges that fail at random (architecture audit, 2026-10-23).

Every judge call answers, raises, runs out of time, comes from the fallback model or returns junk,
chosen by a seeded draw, so a failure here replays exactly. Whatever the judges do, a turn keeps its
invariants: their message is stored once, it ends in a reply or a reaction, nothing escapes, and a
judge that always fails changes nothing the talker is sent compared with having no judge at all.
"""

from __future__ import annotations

import asyncio
import random
import re
from datetime import timedelta
from pathlib import Path

import pytest

from companion.core.extractor import FALLBACK, Extraction
from companion.core.turn.ack import ReactAndReply, Reaction, ThenSend
from companion.core.types import Json, Speaker, TurnId
from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Talker

MESSAGES = (
    "hey, how's your day",
    "*waves at you*",
    "*sits down next to you*",
    "do you remember my dog's name?",
    "remind me at 8pm to call my sister",
    "you know what time it is?",
    "come here cutie",
    "*bonk* behave, i'm hungry",
    "i had a really rough day at work and i don't know what to do",
    "ok",
    "lol",
    "what should i cook tonight?",
)
KINDS = ("answer", "answer", "answer", "raise", "timeout", "fallback", "junk")


def _fill(schema: Json, rng: random.Random) -> Json:
    """A plausible answer for a JSON schema: what a working judge might say."""
    if not isinstance(schema, dict):
        return None
    if "enum" in schema and isinstance(schema["enum"], list):
        return rng.choice(schema["enum"])
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties")
        return {k: _fill(v, rng) for k, v in props.items()} if isinstance(props, dict) else {}
    if kind == "boolean":
        return rng.random() < 0.5
    if kind == "integer":
        low = schema.get("minimum", 0)
        high = schema.get("maximum", 3)
        return rng.randint(low, high) if isinstance(low, int) and isinstance(high, int) else 0
    if kind == "number":
        return round(rng.random(), 2)
    if kind == "array":
        return []
    return "something"


class Chaos:
    """A judge whose every call is drawn from KINDS, or always the one kind given."""

    def __init__(self, seed: int, *, only: str | None = None) -> None:
        self.rng, self.only = random.Random(seed), only
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        self.calls += 1
        kind = self.only or self.rng.choice(KINDS)
        if kind == "raise":
            msg = "judge down"
            raise RuntimeError(msg)
        if kind == "timeout":
            raise TimeoutError
        if kind == "junk":
            return Extraction("not json at all", "j", 0.0, 1)
        model = f"j{FALLBACK}" if kind == "fallback" else "j"
        return Extraction(_fill(schema, self.rng), model, 0.0, 1)


def _unvaried(card: str) -> str:
    """The card without the length limit, which is varied per turn from its random id (T16)."""
    return re.sub(r"under about \d+ words", "under about N words", card)


def _floor_withheld(store: Store, turn: TurnId) -> bool:
    """The one case a turn may end without a reply: the floor held it and read all three drafts
    as intimate, or could not read them, which counts the same (ADR 0017)."""
    for d in store.decisions_for_turn(REL, turn):
        if d.has_key("floor: held reply") and isinstance(d.detail, dict):
            discarded = d.detail.get("discarded")
            return isinstance(discarded, list) and len(discarded) == 3
    return False


async def _settled(convo: Conversation) -> None:
    if convo.habits.pending is not None:
        await asyncio.gather(convo.habits.pending, return_exceptions=True)


def _conversation(store: Store, judge: Chaos | None, talker: Talker) -> Conversation:
    return Conversation(
        store,
        talker,
        PREFIX,
        REL,
        judge=judge,
        roleplay_talker=Talker(),
        route_intimate=True,
        mood="on",
        resample=True,
        relevance="on",
        episodes="on",
        crisis="on",
    )


@pytest.mark.parametrize("seed", range(25))
async def test_whatever_the_judges_do_each_turn_keeps_its_invariants(
    tmp_path: Path, seed: int
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    talker = Talker()
    convo = _conversation(store, Chaos(seed), talker)
    order = random.Random(seed).sample(MESSAGES, len(MESSAGES))
    for i, text in enumerate(order):
        now = NOW + timedelta(minutes=3 * i)
        out = await asyncio.wait_for(handle(convo, SESSION, text, "test", now), 20)
        history = store.history_before(REL, now + timedelta(minutes=1), 500)
        theirs = [u for u in history if u.speaker is Speaker.USER]
        assert [u.text for u in theirs].count(text) == order[: i + 1].count(text), text
        assert len(theirs) == i + 1  # stored exactly once, never twice or lost
        assert isinstance(out, str | Reaction | ReactAndReply | ThenSend)
        if not isinstance(out, Reaction):
            turn = theirs[-1].turn_id
            replied = any(u.turn_id == turn for u in history if u.speaker is Speaker.COMPANION)
            assert replied or _floor_withheld(store, turn), text
    await _settled(convo)
    store.close()


async def test_a_judge_that_always_fails_sends_the_talker_what_no_judge_would(
    tmp_path: Path,
) -> None:
    sent: dict[str, list[tuple[str, str]]] = {}
    for name, judge in (("none", None), ("fails", Chaos(0, only="raise"))):
        store = Store(tmp_path / f"{name}.sqlite")
        talker = Talker()
        convo = _conversation(store, judge, talker)
        for i, text in enumerate(MESSAGES):
            await handle(convo, SESSION, text, "test", NOW + timedelta(minutes=3 * i))
        sent[name] = [(_unvaried(r.card), r.tail) for r in talker.seen]
        await _settled(convo)
    store.close()
    assert sent["fails"] == sent["none"]


async def test_a_turn_that_fails_after_listening_still_keeps_their_message_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import companion.turn.fast as fast  # noqa: PLC0415

    async def broken(*_: object) -> None:
        msg = "look-ups broke"
        raise RuntimeError(msg)

    monkeypatch.setattr(fast, "look", broken)
    store = Store(tmp_path / "rel.sqlite")
    convo = _conversation(store, Chaos(1, only="answer"), Talker())
    with pytest.raises(RuntimeError, match="look-ups broke"):
        await handle(convo, SESSION, "hey there", "test", NOW)
    theirs = [u for u in store.history_before(REL, NOW + timedelta(minutes=1), 10)]
    assert [(u.speaker, u.text, u.frame.value) for u in theirs] == [
        (Speaker.USER, "hey there", "real")
    ]
    await _settled(convo)
    store.close()
