from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json, RelationshipId, SessionId
from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

REL = RelationshipId("rel")
NOW = datetime(2026, 10, 19, 17, 0, tzinfo=UTC)
PREFIX = build_prefix("You are a companion. " * 300)
JOKE = "ugh, crispy fries 😭 the sandwich had to carry the meal on its own"
PLAIN = "ugh, too crispy is the worst"


class Talker:
    """Answers with each of `replies` in turn."""

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls = 0

    async def reply(self, request: TalkerRequest) -> Reply:
        del request
        text = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return Reply(text=text, model="fake", latency_ms=1)


class Judge:
    def __init__(self, severity: int = 0, *, joke: bool = False, generic: bool = False) -> None:
        self.severity, self.joke = severity, joke
        self.generic = generic
        self.quip_calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        props = schema["properties"]
        assert isinstance(props, dict)
        data: Json = None
        if "severity" in props:
            data = {
                "severity": self.severity,
                "stance": "other",
                "vague": False,
                "medical": False,
                "rude": False,
                "recall": False,
                "topic": "",
            }
        elif "added_joke" in props:
            self.quip_calls += 1
            data = {"added_joke": self.joke, "generic": self.generic}
        return Extraction(data=data, model="j", cost_usd=0.0, latency_ms=1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def _say(store: Store, talker: Talker, judge: Judge, *, on: bool = True) -> str:
    convo = Conversation(store, talker, PREFIX, REL, judge=judge, resample=on)
    sent = await handle(convo, SessionId("s"), "kinda too crispy/hard", "test", NOW)
    assert isinstance(sent, str)
    return sent


def _reasons(store: Store) -> list[str]:
    [turn] = {u.turn_id for u in store.history_before(REL, NOW.replace(hour=23), 5)}
    return [
        d.reason
        for d in store.decisions_for_turn(REL, turn)
        if d.reason.startswith(("resampled", "kept:"))
    ]


async def test_a_bolted_on_joke_is_drawn_once_more_and_the_first_is_kept_in_the_log(
    store: Store,
) -> None:
    talker = Talker(JOKE, PLAIN)
    assert await _say(store, talker, Judge(joke=True)) == PLAIN
    assert talker.calls == 2
    assert _reasons(store) == ["resampled: a joke bolted onto an ordinary message"]


async def test_the_second_reply_is_sent_whatever_it_is(store: Store) -> None:
    talker = Talker(JOKE, JOKE)
    assert await _say(store, talker, Judge(joke=True)) == JOKE
    assert talker.calls == 2


async def test_an_em_dash_is_caught_by_code_without_asking_the_judge(store: Store) -> None:
    judge = Judge()
    talker = Talker("ugh—too crispy", PLAIN)
    assert await _say(store, talker, judge) == PLAIN
    assert judge.quip_calls == 0
    assert _reasons(store) == ["resampled: an em dash"]


async def test_a_passing_reply_is_sent_and_logged_as_kept(store: Store) -> None:
    talker = Talker(PLAIN)
    assert await _say(store, talker, Judge()) == PLAIN
    assert talker.calls == 1
    assert _reasons(store) == ["kept: the reply passed its checks"]


async def test_resample_off_is_never_checked(store: Store) -> None:
    judge = Judge(0, joke=True)
    talker = Talker("ugh—" + JOKE, PLAIN)
    assert await _say(store, talker, judge, on=False) == "ugh—" + JOKE
    assert (talker.calls, judge.quip_calls) == (1, 0)
    assert _reasons(store) == []


async def test_a_serious_turn_gets_the_code_checks_but_never_the_joke_judge(store: Store) -> None:
    judge = Judge(2, joke=True)
    talker = Talker("that sounds hard, especially when you're tired", PLAIN)
    assert await _say(store, talker, judge) == PLAIN
    assert judge.quip_calls == 0
    assert _reasons(store) == ["resampled: the stock 'X, especially when' line"]
    clean = Talker(JOKE)
    assert (
        await _say(store, clean, Judge(2, joke=True)) == JOKE
    )  # no code check fails: kept, unlogged
    assert clean.calls == 1


async def test_an_empty_reply_is_drawn_once_more_instead_of_a_silent_turn(store: Store) -> None:
    talker = Talker("", PLAIN)
    assert await _say(store, talker, Judge()) == PLAIN
    assert talker.calls == 2
    assert "resampled: the model returned no text" in _reasons(store)


async def test_a_redraw_that_still_has_an_em_dash_is_drawn_once_more(store: Store) -> None:
    talker = Talker("ugh—too crispy", "still—crispy", PLAIN)
    assert await _say(store, talker, Judge()) == PLAIN
    assert talker.calls == 3


async def test_the_third_draw_is_sent_whatever_it_is(store: Store) -> None:
    talker = Talker("a—b", "c—d", "e—f")
    assert await _say(store, talker, Judge()) == "e—f"
    assert talker.calls == 3


async def test_an_acute_turn_gets_the_code_checks_too(store: Store) -> None:
    judge = Judge(3, joke=True)
    talker = Talker("i hear you—please stay with me", PLAIN)
    assert await _say(store, talker, judge) == PLAIN
    assert judge.quip_calls == 0
    assert _reasons(store) == ["resampled: an em dash"]


async def test_a_canned_generic_reaction_is_drawn_once_more(store: Store) -> None:
    judge = Judge(0, generic=True)
    talker = Talker("ooh, that sounds so good", PLAIN)
    assert await _say(store, talker, judge) == PLAIN
    assert _reasons(store) == ["resampled: a canned generic reaction"]
