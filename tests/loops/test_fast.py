from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    DecisionKind,
    Evidence,
    Frame,
    Provenance,
    RelationshipId,
    SessionId,
    Speaker,
    Subject,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.loops.fast import Conversation
from companion.models.anthropic import AnthropicTalker
from companion.models.openrouter import OpenRouterTalker
from companion.store.sqlite import replay as store_replay
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


class FakeTalker:
    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply(text=self.texts.pop(0), model="fake", latency_ms=5)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def test_turns_are_logged_and_replay_matches(store: Store, tmp_path: Path) -> None:
    talker = FakeTalker("hey", "couldn't sleep either?", "ha, fair")
    convo = Conversation(store, talker, PREFIX, REL)
    for i, text in enumerate(["morning", "up early", "yeah"]):
        await convo.handle(SESSION, text, "test", NOW + timedelta(minutes=i))
    assert len(talker.seen[2].messages) == 5  # two earlier exchanges plus the new message
    store.close()
    for turn_id in _turn_ids(tmp_path / "rel.sqlite"):
        report = store_replay.replay_file(tmp_path / "rel.sqlite", turn_id)
        assert report.matched
        assert [d.kind for d in report.decisions] == [DecisionKind.POLICY]


async def test_empty_model_reply_is_logged_not_sent(store: Store, tmp_path: Path) -> None:
    convo = Conversation(store, FakeTalker(""), PREFIX, REL)
    assert await convo.handle(SESSION, "hello", "test", NOW) == ""
    store.close()
    report = store_replay.replay_file(
        tmp_path / "rel.sqlite", _turn_ids(tmp_path / "rel.sqlite")[0]
    )
    assert [d.kind for d in report.decisions] == [DecisionKind.DO_NOTHING]


def _turn_ids(db: Path) -> list[str]:
    import sqlite3  # noqa: PLC0415

    with sqlite3.connect(db) as c:
        return [r[0] for r in c.execute("SELECT turn_id FROM turn_requests ORDER BY at")]


def _request() -> TalkerRequest:
    from companion.core.prompt.request import build_request  # noqa: PLC0415

    return build_request(PREFIX, [], "hi")


async def test_anthropic_body_has_cached_system_and_no_thinking() -> None:
    sent: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        sent.update(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "model": "m",
                "content": [{"type": "text", "text": " hi "}],
                "usage": {"input_tokens": 7, "cache_read_input_tokens": 5},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reply = await AnthropicTalker("k", client).reply(_request())
    assert reply.text == "hi"
    assert reply.cache_read_tokens == 5
    assert "thinking" not in sent
    assert sent["system"][0]["cache_control"] == {"type": "ephemeral"}  # type: ignore[index]


async def test_openrouter_pins_provider_and_disables_reasoning() -> None:
    sent: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        sent.update(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "model": "anthropic/claude-haiku-4.5",
                "choices": [{"message": {"content": "hi"}}],
                "usage": {"prompt_tokens": 9, "prompt_tokens_details": {"cached_tokens": 4}},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reply = await OpenRouterTalker("k", client, "anthropic/claude-haiku-5.5").reply(_request())
    assert reply.text == "hi"
    assert reply.cache_read_tokens == 4
    assert sent["provider"] == {"order": ["Anthropic"], "allow_fallbacks": False}
    assert sent["reasoning"] == {"enabled": False}


async def test_history_window_is_shared_by_live_and_replay(store: Store, tmp_path: Path) -> None:
    from companion.core.history import HISTORY_LIMIT  # noqa: PLC0415

    turns = HISTORY_LIMIT  # enough that the window must have cut off the start
    talker = FakeTalker(*(f"r{i}" for i in range(turns)))
    convo = Conversation(store, talker, PREFIX, REL)
    for i in range(turns):
        await convo.handle(SESSION, f"m{i}", "test", NOW + timedelta(minutes=i))
    assert len(talker.seen[-1].messages) == HISTORY_LIMIT + 1
    store.close()
    db = tmp_path / "rel.sqlite"
    assert all(store_replay.replay_file(db, t).matched for t in _turn_ids(db))


async def test_history_continues_across_sessions(store: Store) -> None:
    talker = FakeTalker("a", "b")
    convo = Conversation(store, talker, PREFIX, REL)
    await convo.handle(SessionId("monday"), "first", "test", NOW)
    await convo.handle(SessionId("tuesday"), "second", "test", NOW + timedelta(days=1))
    assert [m.content.split("\n\n")[-1] for m in talker.seen[1].messages] == [
        "first",
        "a",
        "second",
    ]


async def test_clock_line_names_the_gap(store: Store) -> None:
    talker = FakeTalker("a", "b")
    convo = Conversation(store, talker, PREFIX, REL)
    await convo.handle(SESSION, "first", "test", NOW)
    await convo.handle(SESSION, "second", "test", NOW + timedelta(hours=5, minutes=1))
    assert "last message 5 hours ago" in talker.seen[1].messages[-1].content


async def test_beliefs_reach_the_request_and_each_placement_is_logged(
    store: Store, tmp_path: Path
) -> None:
    base = Utterance(
        UtteranceId("old"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "i have ocd and i like climbing",
        Frame.REAL,
        "test",
        NOW - timedelta(days=1),
    )
    store.append_utterance(base)

    def believe(bid: str, claim: str, quote: str, sens: int) -> Belief:
        return Belief(
            id=BeliefId(bid),
            relationship_id=REL,
            subject=Subject.USER,
            kind=BeliefKind.TRAIT,
            claim=claim,
            evidence=(Evidence(base.id, quote),),
            provenance=Provenance.STATED,
            speaker=Speaker.USER,
            frame=Frame.REAL,
            confidence=0.6,
            valid_from=base.at,
            recorded_at=base.at,
            sensitivity=sens,
        )

    store.insert_belief(believe("b1", "Likes climbing", "i like climbing", 0))
    store.insert_belief(believe("b2", "Has OCD", "i have ocd", 2))
    talker = FakeTalker("nice")
    convo = Conversation(store, talker, PREFIX, REL)
    await convo.handle(SESSION, "hey", "test", NOW)
    sent = talker.seen[0].card
    assert "Likes climbing" not in talker.seen[0].messages[-1].content
    assert "Likes climbing" in sent.split("Also known")[0]
    assert "Has OCD" in sent.split("Also known")[1]
    store.close()
    db = tmp_path / "rel.sqlite"
    [turn_id] = _turn_ids(db)
    report = store_replay.replay_file(db, turn_id)
    assert report.matched
    kinds = {d.belief_id: d.kind for d in report.decisions if d.belief_id}
    assert kinds == {"b1": DecisionKind.SURFACE, "b2": DecisionKind.WITHHOLD}


async def test_stale_beliefs_reach_the_model_as_older_and_every_placement_is_logged(
    store: Store, tmp_path: Path
) -> None:
    base = Utterance(
        UtteranceId("old"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "feeling pretty low and i like climbing",
        Frame.REAL,
        "test",
        NOW - timedelta(days=60),
    )
    store.append_utterance(base)

    def believe(bid: str, claim: str, quote: str, kind: BeliefKind, sens: int) -> Belief:
        return Belief(
            id=BeliefId(bid),
            relationship_id=REL,
            subject=Subject.USER,
            kind=kind,
            claim=claim,
            evidence=(Evidence(base.id, quote),),
            provenance=Provenance.STATED,
            speaker=Speaker.USER,
            frame=Frame.REAL,
            confidence=0.6,
            valid_from=base.at,
            recorded_at=base.at,
            sensitivity=sens,
        )

    store.insert_belief(believe("trait", "Likes climbing", "i like climbing", BeliefKind.TRAIT, 0))
    store.insert_belief(believe("mood", "Feels low", "feeling pretty low", BeliefKind.STATE, 0))
    store.insert_belief(believe("hush", "Feels very low", "pretty low", BeliefKind.STATE, 2))
    talker = FakeTalker("hey")
    await Conversation(store, talker, PREFIX, REL).handle(SESSION, "hi", "test", NOW)
    sent = talker.seen[0].card
    main = sent.split("[Older")[0]
    assert "Likes climbing (mentioned 2 months ago)" in main
    assert "Feels low" not in main
    assert "[Older, and may be out of date" in sent
    assert "Feels low (mentioned 2 months ago)" in sent.split("[Older")[1]
    assert "Feels very low" not in sent  # sensitive and stale: left out entirely
    store.close()
    db = tmp_path / "rel.sqlite"
    report = store_replay.replay_file(db, _turn_ids(db)[0])
    assert report.matched
    by_belief = {str(d.belief_id): (d.kind, d.reason) for d in report.decisions if d.belief_id}
    assert by_belief["trait"][0] is DecisionKind.SURFACE
    assert by_belief["mood"] == (DecisionKind.SURFACE, "in the card as older, possibly out of date")
    assert by_belief["hush"][0] is DecisionKind.WITHHOLD
    assert "stale" in by_belief["hush"][1]
    assert "14-day horizon" in by_belief["hush"][1]


async def test_a_streak_of_the_same_opener_reaches_the_next_request_as_a_note(
    store: Store,
) -> None:
    talker = FakeTalker("Ha, one", "Ha, two", "Ha, three", "fine")
    convo = Conversation(store, talker, PREFIX, REL)
    for i, text in enumerate(["a", "b", "c", "d"]):
        await convo.handle(SESSION, text, "test", NOW + timedelta(minutes=i))
    assert "began with" not in talker.seen[2].messages[-1].content
    assert 'began with "ha"' in talker.seen[3].messages[-1].content
    store.close()


async def test_openrouter_does_not_pin_a_provider_for_other_makers() -> None:
    sent: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        sent.update(json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await OpenRouterTalker("k", client, "openai/gpt-6-luna").reply(_request())
    assert "provider" not in sent
    assert sent["reasoning"] == {"enabled": False}
