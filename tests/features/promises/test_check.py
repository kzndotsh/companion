from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import (
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.promises.logic import Check, Kind, Promise, Scope, check_input, read_check
from companion.features.promises.run import KEPT, WOULD_REDRAW, WOULD_RETIRE
from companion.kit.beside import settled
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

REL = RelationshipId("rel")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 11, 3, 15, 0, tzinfo=UTC)


class Talker:
    async def reply(self, request: TalkerRequest) -> Reply:
        del request
        return Reply(text="four coffees before noon, impressive", model="fake", latency_ms=1)


class Judge:
    """Answers the promise check as told; the other judges get nothing they can read."""

    def __init__(self, answer: Json) -> None:
        self.answer = answer
        self.checks: list[str] = []

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system
        props = schema.get("properties")
        if isinstance(props, dict) and "broken" in props:
            self.checks.append(user)
            return Extraction(self.answer, "judge", 0.0, 1)
        return Extraction(None, "judge", 0.0, 1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SessionId("s"),
        TurnId("t0"),
        Speaker.COMPANION,
        "ok i'll retire the coffee bit",
        Frame.REAL,
        "test",
        NOW - timedelta(days=1),
    )
    s.append_utterance(said)
    promise = Promise(
        "p-coffee",
        REL,
        said.id,
        "ok i'll retire the coffee bit",
        "It will retire the coffee joke.",
        Kind.STANDING,
        "coffee",
        said.at,
    )
    s.add_promise(promise, model="m", prompt="system/promise-read@v1", at=said.at)
    return s


async def _turn(store: Store, judge: Judge, *, promises: str = "shadow") -> list[str]:
    runtime = Runtime(store, Talker(), PREFIX, REL, judge=judge, promises=promises)
    await handle(runtime, SessionId("s"), "how did my morning look to you", "test", NOW)
    await settled()
    return [d.reason for d in store.decisions_with_key(REL, WOULD_REDRAW)] + [
        d.reason for d in store.decisions_with_key(REL, KEPT)
    ]


async def test_a_reply_that_breaks_a_promise_is_logged_as_one_it_would_redraw(
    store: Store,
) -> None:
    judge = Judge({"broken": "p1", "released": [], "why": "the same joke"})
    reasons = await _turn(store, judge)
    assert reasons == [f"{WOULD_REDRAW}: it breaks It will retire the coffee joke."]
    assert 'p1: "ok i\'ll retire the coffee bit"' in judge.checks[0]
    assert "Reply: four coffees before noon, impressive" in judge.checks[0]


async def test_a_reply_that_keeps_them_is_logged_as_kept(store: Store) -> None:
    reasons = await _turn(store, Judge({"broken": "none", "released": [], "why": "fine"}))
    assert reasons == [f"{KEPT}: 1 promises read"]


async def test_a_released_promise_is_logged_as_one_it_would_retire(store: Store) -> None:
    await _turn(store, Judge({"broken": "none", "released": ["p1"], "why": "they asked"}))
    (retire,) = store.decisions_with_key(REL, WOULD_RETIRE)
    assert (retire.detail or {}).get("promise_id") == "p-coffee"
    assert [r.mark for r in store.promises(REL)] == [None]  # shadow: nothing is retired


async def test_off_or_no_promises_or_an_unreadable_answer_logs_nothing(store: Store) -> None:
    judge = Judge({"broken": "p1", "released": [], "why": "x"})
    assert await _turn(store, judge, promises="off") == []
    assert judge.checks == []
    assert await _turn(store, Judge({"nonsense": True})) == []


def test_the_answer_is_read_as_labels_or_refused() -> None:
    assert read_check({"broken": "None", "released": [], "why": ""}) == Check(None, (), "")
    assert read_check({"broken": "P2", "released": ["p1", 3], "why": "w"}) == Check(
        "p2", ("p1",), "w"
    )
    assert read_check({"broken": "p1"}) is None
    assert read_check("p1") is None


def test_the_input_labels_each_promise_and_ends_with_the_reply() -> None:
    p = Promise(
        "x", REL, UtteranceId("u"), "no more puns", "It stops punning.", Kind.STANDING, "", NOW
    )
    text, labels = check_input([p], [(Speaker.USER, "hey"), (Speaker.COMPANION, "hi")], "a pun")
    assert labels == {"p1": p}
    assert text.splitlines() == [
        "Promises:",
        '- p1: "no more puns"',
        "Newest messages:",
        "them: hey",
        "companion: hi",
        "Reply: a pun",
    ]


async def test_a_moment_promise_is_not_checked_once_its_week_is_over(store: Store) -> None:
    (only,) = store.promises(REL)
    store.set_promise_scope(only.promise.id, Scope.MOMENT, "owner", NOW)
    judge = Judge({"broken": "p1", "released": [], "why": "x"})
    later = Runtime(store, Talker(), PREFIX, REL, judge=judge, promises="shadow")
    await handle(later, SessionId("s"), "morning", "test", NOW + timedelta(days=7))
    await settled()
    assert judge.checks == []
    assert store.decisions_with_key(REL, WOULD_REDRAW) == []
