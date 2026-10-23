from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.spend import SpendEvent
from companion.core.talker import Reply
from companion.core.types import RelationshipId, SessionId, Speaker
from companion.loops.conversation import Conversation
from companion.loops.spendcap import NOTICE, over_cap
from companion.settings import Settings
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOON = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


class Talker:
    def __init__(self) -> None:
        self.calls = 0

    async def reply(self, request: TalkerRequest) -> Reply:
        del request
        self.calls += 1
        return Reply(text="hi", model="m", latency_ms=1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _spend(store: Store, dollars: float, at: datetime) -> None:
    store.record_spend(REL, SpendEvent("talker", "m", dollars, 0), at)


async def test_under_the_cap_the_turn_runs_as_usual(store: Store) -> None:
    _spend(store, 1.0, NOON - timedelta(minutes=5))
    talker = Talker()
    convo = Conversation(store, talker, PREFIX, REL, daily_cap_usd=10.0)
    assert await handle(convo, SESSION, "hey", "t", NOON) == "hi"
    assert talker.calls == 1


async def test_at_the_cap_nothing_paid_runs_and_the_user_is_told_once(store: Store) -> None:
    _spend(store, 10.0, NOON - timedelta(minutes=5))
    talker = Talker()
    convo = Conversation(store, talker, PREFIX, REL, daily_cap_usd=10.0)
    assert await handle(convo, SESSION, "hey", "t", NOON) == NOTICE
    assert await handle(convo, SESSION, "still there?", "t", NOON + timedelta(minutes=1)) == ""
    assert talker.calls == 0


async def test_a_message_sent_at_the_cap_is_kept_and_the_notice_is_not_remembered_as_said(
    store: Store,
) -> None:
    _spend(store, 10.0, NOON - timedelta(minutes=5))
    convo = Conversation(store, Talker(), PREFIX, REL, daily_cap_usd=10.0)
    await handle(convo, SESSION, "hey", "t", NOON)
    said = [(u.speaker, u.text) for u in store.history_before(REL, NOON + timedelta(days=1), 10)]
    assert said == [(Speaker.USER, "hey")]


async def test_the_refusal_is_a_logged_decision_with_a_reason_written_by_code(
    store: Store,
) -> None:
    _spend(store, 12.5, NOON - timedelta(minutes=5))
    convo = Conversation(store, Talker(), PREFIX, REL, daily_cap_usd=10.0)
    await handle(convo, SESSION, "hey", "t", NOON)
    reasons = [d.reason for d in store.decisions_for_turn(REL, _last_turn(store))]
    assert reasons == ["daily spend cap reached: $12.50 of $10.00, no reply"]


def _last_turn(store: Store):  # type: ignore[no-untyped-def]
    [last] = store.history_before(REL, NOON + timedelta(days=1), 1)
    return last.turn_id


async def test_the_next_day_the_bot_answers_again(store: Store) -> None:
    _spend(store, 10.0, NOON - timedelta(minutes=5))
    talker = Talker()
    convo = Conversation(store, talker, PREFIX, REL, daily_cap_usd=10.0)
    await handle(convo, SESSION, "hey", "t", NOON)
    assert await handle(convo, SESSION, "morning", "t", NOON + timedelta(days=1)) == "hi"
    assert talker.calls == 1


async def test_no_cap_means_no_limit(store: Store) -> None:
    _spend(store, 500.0, NOON - timedelta(minutes=5))
    convo = Conversation(store, Talker(), PREFIX, REL, daily_cap_usd=None)
    assert await handle(convo, SESSION, "hey", "t", NOON) == "hi"


def test_over_cap_reports_today_only(store: Store) -> None:
    _spend(store, 9.0, NOON - timedelta(days=2))
    _spend(store, 4.0, NOON - timedelta(minutes=1))
    assert over_cap(store, REL, 10.0, NOON) is None
    assert over_cap(store, REL, 4.0, NOON) == pytest.approx(4.0)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, 10.0),
        ("", 10.0),
        ("2.5", 2.5),
        ("off", None),
        ("none", None),
        ("0", None),
        ("junk", 10.0),
    ],
)
def test_the_cap_setting(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: float | None
) -> None:
    if raw is None:
        monkeypatch.delenv("COMPANION_DAILY_CAP_USD", raising=False)
    else:
        monkeypatch.setenv("COMPANION_DAILY_CAP_USD", raw)
    assert Settings.from_env().daily_cap == expected
