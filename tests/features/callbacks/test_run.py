from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Evidence,
    Frame,
    Json,
    Provenance,
    RelationshipId,
    SessionId,
    Speaker,
    Subject,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.callbacks.run import check_new
from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from companion.turn.fast import handle

REL = RelationshipId("rel")
NOW = datetime(2026, 10, 18, 17, 0, tzinfo=UTC)
PREFIX = build_prefix("You are a companion. " * 300)


class Talker:
    async def reply(self, request: TalkerRequest) -> Reply:
        del request
        return Reply(text="oh wait, how did the landlord call go?", model="fake", latency_ms=1)


class Judge:
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, schema
        self.calls += 1
        assert "[m1] The user dreads a call with their landlord." in user
        data: Json = {
            "callback": True,
            "memories": ["m1"],
            "accurate": True,
            "fitting": True,
            "forced": False,
        }
        return Extraction(data=data, model="j", cost_usd=0.001, latency_ms=1)


async def test_each_reply_is_judged_once_and_the_verdict_is_kept(tmp_path: Path) -> None:
    store = Store(tmp_path / "rel.sqlite")
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SessionId("s"),
        TurnId("t0"),
        Speaker.USER,
        "i'm dreading a call with my landlord",
        Frame.REAL,
        "test",
        NOW - timedelta(days=3),
    )
    store.append_utterance(said)
    store.insert_belief(
        Belief(
            id=BeliefId("b1"),
            relationship_id=REL,
            subject=Subject.USER,
            kind=BeliefKind.STATE,
            claim="The user dreads a call with their landlord.",
            evidence=(Evidence(said.id, "dreading a call with my landlord"),),
            provenance=Provenance.STATED,
            speaker=Speaker.USER,
            frame=Frame.REAL,
            confidence=0.7,
            valid_from=said.at,
            recorded_at=said.at,
            sensitivity=0,
        )
    )
    convo = Conversation(store, Talker(), PREFIX, REL)
    await handle(convo, SessionId("s"), "ugh long day", "test", NOW)
    judge = Judge()
    assert await check_new(store, judge, REL, NOW - timedelta(days=1), 1.0) == (1, 0.001)
    assert await check_new(store, judge, REL, NOW - timedelta(days=1), 1.0) == (0, 0.0)
    assert judge.calls == 1
    [(_, check)] = store.callback_checks_since(REL, NOW - timedelta(days=1))
    assert check.landed
    assert check.memories == ("The user dreads a call with their landlord.",)
