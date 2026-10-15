from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.ack import REACT_THRESHOLD, Reaction
from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Json, RelationshipId, SessionId, TurnId
from companion.loops import ack as ack_loop
from companion.loops.fast import Conversation
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


class Talker:
    """`calls` counts replies that finished. A call cancelled mid-flight does not count."""

    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.calls = 0
        self.started = 0

    async def reply(self, request: TalkerRequest) -> Reply:
        self.started += 1
        text = self.texts.pop(0)
        await asyncio.sleep(0.02)
        self.calls += 1
        return Reply(text=text, model="fake", latency_ms=5)


class Judge:
    def __init__(self, data: Json = None, *, fail: bool = False, delay: float = 0.005) -> None:
        self.data = data
        self.fail = fail
        self.delay = delay
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            msg = "provider down"
            raise RuntimeError(msg)
        return Extraction(data=self.data, model="judge-model", cost_usd=0.0, latency_ms=1)


def _verdict(kind: str, confidence: float) -> Json:
    return {"kind": kind, "confidence": confidence, "emoji": "👍"}


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def _two_turns(
    store: Store, judge: Judge | None, first: str = "no rush, tell me later.", second: str = "okie"
) -> tuple[Talker, str | Reaction]:
    talker = Talker(first, "a normal reply")
    convo = Conversation(store, talker, PREFIX, REL, judge=judge)
    await convo.handle(SESSION, "too much to explain rn", "test", NOW)
    out = await convo.handle(SESSION, second, "test", NOW + timedelta(seconds=30))
    return talker, out


def _last_user_turn(store: Store) -> TurnId:
    [last] = store.history_before(REL, NOW + timedelta(days=1), 1)
    return last.turn_id


def _reasons(store: Store) -> list[str]:
    return [d.reason for d in store.decisions_for_turn(REL, _last_user_turn(store))]


async def test_a_confident_ack_is_reacted_to_and_never_reaches_the_talker(store: Store) -> None:
    judge = Judge(_verdict("ack", 0.95))
    talker, out = await _two_turns(store, judge)
    assert out == Reaction("👍")
    assert talker.calls == 1  # only the first turn finished
    assert talker.started == 2  # the second was started in parallel, then cancelled
    assert judge.calls == 1
    assert [u.text for u in store.history_before(REL, NOW + timedelta(days=1), 10)][-1] == "okie"
    assert any("reacted 👍 instead of replying" in r for r in _reasons(store))


async def test_a_reaction_logs_the_scorer_and_scores_but_creates_no_turn_request(
    store: Store,
) -> None:
    await _two_turns(store, Judge(_verdict("ack", 0.95)))
    [d] = store.decisions_for_turn(REL, _last_user_turn(store))
    assert d.detail is not None
    assert d.detail["scorer"] == "judge-model"
    assert d.detail["scores"] == {"kind": "ack", "confidence": 0.95}
    assert d.detail["threshold"] == REACT_THRESHOLD
    assert store.latest_turn(REL) != _last_user_turn(store)


@pytest.mark.parametrize(
    "verdict", [_verdict("ack", 0.6), _verdict("answer", 0.99), _verdict("emotional", 0.99)]
)
async def test_anything_but_a_confident_ack_gets_a_normal_reply(
    store: Store, verdict: Json
) -> None:
    talker, out = await _two_turns(store, Judge(verdict))
    assert out == "a normal reply"
    assert talker.calls == 2
    assert any(r.startswith("replied: judged") for r in _reasons(store))


async def test_the_model_is_not_asked_after_a_question(store: Store) -> None:
    judge = Judge(_verdict("ack", 0.99))
    _, out = await _two_turns(store, judge, first="what are you up to?")
    assert out == "a normal reply"
    assert judge.calls == 0


async def test_a_long_message_is_not_asked_about(store: Store) -> None:
    judge = Judge(_verdict("ack", 0.99))
    _, out = await _two_turns(store, judge, second="ok but actually i have a lot to say")
    assert out == "a normal reply"
    assert judge.calls == 0


async def test_a_failing_judge_means_a_normal_reply(store: Store) -> None:
    talker, out = await _two_turns(store, Judge(fail=True))
    assert out == "a normal reply"
    assert talker.calls == 2


async def test_a_slow_judge_is_abandoned(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ack_loop, "TIMEOUT_SECONDS", 0.05)
    talker, out = await _two_turns(store, Judge(_verdict("ack", 0.99), delay=1.0))
    assert out == "a normal reply"
    assert talker.calls == 2


async def test_a_malformed_judgement_means_a_normal_reply(store: Store) -> None:
    _, out = await _two_turns(store, Judge({"kind": "vibes"}))
    assert out == "a normal reply"


async def test_without_a_judge_everything_gets_a_reply(store: Store) -> None:
    _, out = await _two_turns(store, None)
    assert out == "a normal reply"
