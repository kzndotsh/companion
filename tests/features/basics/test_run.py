from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.turn.address import KEY as ADDRESS_KEY
from companion.core.turn.listening import Judgement
from companion.core.types import (
    Belief,
    Frame,
    Json,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.basics.logic import ASK_NAME, ASK_PRONOUNS, ASKED, ASKED_PRONOUNS
from companion.features.basics.run import basics_offer, capture_pronouns
from companion.loops.conversation import Conversation
from companion.loops.current import Turn
from companion.loops.features import Lookups, Moment, Offer
from companion.store.sqlite.store import Store
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Talker

NAMED = "The user's name is Sam."


class Reader:
    """Answers the pronoun capture with a fixed reading."""

    def __init__(self, pronouns: str) -> None:
        self.pronouns, self.asked = pronouns, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.asked += 1
        return Extraction(data={"pronouns": self.pronouns}, model="j", cost_usd=0.0, latency_ms=1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _note(
    store: Store, beliefs: list[Belief], *, severity: int = 0, check_in: bool = False
) -> tuple[str, ...]:
    convo = Conversation(store, Talker(), PREFIX, REL)
    t = Turn(SESSION, TurnId("t"), NOW, [], "just got home")
    heard = (Judgement(severity, "other", vague=False), "j", "")
    m = Moment(convo, t, Frame.REAL, heard, Lookups(), False, beliefs)
    so_far = {"check-in": Offer(("[check in]",) if check_in else ())}
    offer = basics_offer(m, None, so_far)
    for write in offer.after:
        write()
    return offer.lines


def test_the_name_comes_first_and_pronouns_wait_a_day_after_it(
    store: Store, belief: Callable[..., Belief]
) -> None:
    assert _note(store, []) == (ASK_NAME.text,)  # the name alone, never both on one turn
    named = [belief(bid="n", claim=NAMED)]
    assert _note(store, named) == ()  # known now, but the name was asked today


def test_the_pronoun_note_needs_the_setting_unset_and_comes_once_a_day(
    tmp_path: Path, belief: Callable[..., Belief]
) -> None:
    named = [belief(bid="n", claim=NAMED)]
    store = Store(tmp_path / "a.sqlite")
    assert _note(store, named, severity=1) == ()  # not on a serious turn
    assert _note(store, named, check_in=True) == ()
    assert _note(store, named) == (ASK_PRONOUNS.text,)
    assert store.decided_since(REL, ASKED_PRONOUNS, NOW)
    assert not store.decided_since(REL, ASKED, NOW - timedelta(days=1))
    assert _note(store, named) == ()  # asked today
    set_already = Store(tmp_path / "b.sqlite")
    set_already.set_setting(REL, ADDRESS_KEY, "he/him", NOW - timedelta(days=3))
    assert _note(set_already, named) == ()


async def _capture(store: Store, reader: Reader, asked: str, said: str) -> None:
    prior = [
        Utterance(
            UtteranceId("c1"),
            REL,
            SESSION,
            TurnId("t0"),
            Speaker.COMPANION,
            asked,
            Frame.REAL,
            "test",
            NOW - timedelta(minutes=1),
        )
    ]
    convo = Conversation(store, Talker(), PREFIX, REL, judge=reader)
    await capture_pronouns(convo, Turn(SESSION, TurnId("t1"), NOW, prior, said))


async def test_capture_sets_how_to_refer_to_them_from_their_own_words(store: Store) -> None:
    await _capture(store, Reader("she/her"), "oh nice! which pronouns do you use?", "she/her :)")
    assert store.setting(REL, ADDRESS_KEY) == "she/her"
    assert store.decided_since(REL, "basics: pronoun capture", NOW)


async def test_capture_ignores_a_reading_not_in_their_message(store: Store) -> None:
    await _capture(store, Reader("they/them"), "what pronouns do you go by?", "lol why")
    assert store.setting(REL, ADDRESS_KEY) is None
    assert store.decided_since(REL, "basics: pronoun capture", NOW)  # logged either way


async def test_capture_does_nothing_when_the_setting_is_set(store: Store) -> None:
    store.set_setting(REL, ADDRESS_KEY, "he/him", NOW - timedelta(days=1))
    reader = Reader("she/her")
    await _capture(store, reader, "which pronouns do you use?", "she/her")
    assert reader.asked == 0
    assert store.setting(REL, ADDRESS_KEY) == "he/him"


async def test_capture_waits_for_a_pronoun_question(store: Store) -> None:
    reader = Reader("she/her")
    await _capture(store, reader, "what should i call you?", "she/her")
    assert reader.asked == 0
