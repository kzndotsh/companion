"""What a failure leaves behind. The audits found small teams ship the same four bugs: error text
stored as something the companion said, a partial reply kept, a lost user message and a
duplicate turn."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import RelationshipId, SessionId, Speaker
from companion.loops.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


class Flaky:
    def __init__(self, *outcomes: str | Exception) -> None:
        self.outcomes = list(outcomes)
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return Reply(text=outcome, model="m", latency_ms=1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _said(store: Store) -> list[tuple[Speaker, str]]:
    return [(u.speaker, u.text) for u in store.history_before(REL, NOW + timedelta(days=1), 50)]


async def test_a_failed_model_call_keeps_the_users_message_and_stores_nothing_from_the_error(
    store: Store,
) -> None:
    runtime = Runtime(store, Flaky(RuntimeError("provider down: 503")), PREFIX, REL)
    with pytest.raises(RuntimeError):
        await handle(runtime, SESSION, "are you there", "t", NOW)
    assert _said(store) == [(Speaker.USER, "are you there")]
    assert store.latest_turn(REL) is None  # no request record for a turn that never answered


async def test_the_next_turn_sees_the_unanswered_message_exactly_once(store: Store) -> None:
    talker = Flaky(RuntimeError("down"), "hi, sorry about that")
    runtime = Runtime(store, talker, PREFIX, REL)
    with pytest.raises(RuntimeError):
        await handle(runtime, SESSION, "are you there", "t", NOW)
    await handle(runtime, SESSION, "hello?", "t", NOW + timedelta(minutes=2))
    history = [m.content for m in talker.seen[1].messages]
    assert history.count("are you there") == 1
    assert history[-1] == "hello?"
    assert [t for s, t in _said(store) if s is Speaker.COMPANION] == ["hi, sorry about that"]


async def test_an_empty_reply_stores_no_companion_message(store: Store) -> None:
    runtime = Runtime(store, Flaky(""), PREFIX, REL)
    await handle(runtime, SESSION, "hey", "t", NOW)
    assert _said(store) == [(Speaker.USER, "hey")]


async def test_one_message_makes_one_turn_and_one_reply(store: Store) -> None:
    runtime = Runtime(store, Flaky("hi"), PREFIX, REL)
    await handle(runtime, SESSION, "hey", "t", NOW)
    assert _said(store) == [(Speaker.USER, "hey"), (Speaker.COMPANION, "hi")]
