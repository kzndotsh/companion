from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
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
from companion.core.views import card_views, is_settled
from companion.loops.curate import rebuild
from companion.loops.fast import Conversation
from companion.loops.slow import reflect_once
from companion.store.sqlite import replay as store_replay
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
T0 = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
PREFIX = build_prefix("You are steady and warm. " * 200)
VIEW_TEXT = "i don't think lazy is a flaw, it's a preference for how you spend energy"


class Routed:
    """Answers the user pass and the self pass separately, and records every prompt."""

    def __init__(self, users: list[Json] | None = None, views: list[Json] | None = None) -> None:
        self.users = list(users or [])
        self.views = list(views or [])
        self.prompts: dict[str, list[str]] = {"user": [], "self": []}

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        which = "self" if "views the COMPANION expressed" in system else "user"
        self.prompts[which].append(user)
        queue = self.views if which == "self" else self.users
        data: Json = queue.pop(0) if queue else {"beliefs": []}
        return Extraction(data, "fake", 0.0, 1)


def _say(store: Store, n: int, speaker: Speaker, text: str) -> Utterance:
    u = Utterance(
        UtteranceId(f"u{n}"),
        REL,
        SessionId("s"),
        TurnId(f"t{n}"),
        speaker,
        text,
        Frame.REAL,
        "test",
        T0 + timedelta(minutes=n),
    )
    store.append_utterance(u)
    return u


def _view(
    ref: str, quote: str, claim: str = "The companion thinks laziness is not a flaw."
) -> Json:
    return {
        "beliefs": [
            {
                "ref": ref,
                "quote": quote,
                "claim": claim,
                "kind": "preference",
                "confidence": 0.8,
                "grounding": "own_reasoning",
            }
        ]
    }


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def test_a_view_is_recorded_from_the_companions_own_words(store: Store) -> None:
    _say(store, 1, Speaker.USER, "lazy is a character flaw tho")
    _say(store, 2, Speaker.COMPANION, VIEW_TEXT)
    ex = Routed(views=[_view("m2", "lazy is a flaw")])
    result = await reflect_once(store, ex, REL)
    assert (result.views_accepted, result.views_rejected) == (1, 0)
    [v] = store.self_beliefs(REL)
    assert (v.subject, v.speaker, v.provenance) == (
        Subject.SELF,
        Speaker.COMPANION,
        Provenance.COMPANION_SAID,
    )
    assert v.evidence[0].utterance_id == "u2"
    assert store.user_beliefs(REL) == []


async def test_a_view_cannot_be_quoted_from_the_users_message(store: Store) -> None:
    _say(store, 1, Speaker.USER, "lazy is a character flaw tho")
    _say(store, 2, Speaker.COMPANION, VIEW_TEXT)
    ex = Routed(views=[_view("m1", "lazy is a character flaw")])
    result = await reflect_once(store, ex, REL)
    assert (result.views_accepted, result.views_rejected) == (0, 1)
    assert store.self_beliefs(REL) == []


async def test_the_user_pass_never_sees_the_companions_views(store: Store) -> None:
    _say(store, 1, Speaker.COMPANION, VIEW_TEXT)
    await reflect_once(store, Routed(views=[_view("m1", "lazy is a flaw")]), REL)
    _say(store, 2, Speaker.USER, "i like climbing")
    spy = Routed()
    await reflect_once(store, spy, REL)
    assert "laziness" not in spy.prompts["user"][0]


async def test_a_view_is_tentative_until_restated_on_another_day(store: Store) -> None:
    _say(store, 1, Speaker.COMPANION, VIEW_TEXT)
    await reflect_once(store, Routed(views=[_view("m1", "lazy is a flaw")]), REL)
    [v] = store.self_beliefs(REL)
    assert not is_settled(v, store.evidence_days(REL))

    _say(store, 60 * 30, Speaker.COMPANION, "still think lazy is a flaw? no. it's about energy")
    restated: Json = {
        "beliefs": [
            {
                "ref": "m2",
                "quote": "it's about energy",
                "kind": "preference",
                "confidence": 0.8,
                "grounding": "own_reasoning",
                "claim": "The companion thinks laziness is not a flaw.",
                "confirms": "k1",
            }
        ]
    }
    result = await reflect_once(store, Routed(views=[restated]), REL)
    assert result.views_confirmed == 1
    assert len(store.self_beliefs(REL)) == 1
    assert is_settled(store.self_beliefs(REL)[0], store.evidence_days(REL))
    assert card_views(store.self_beliefs(REL), set(), store.last_support(REL)) == ()


async def test_a_rebuild_restates_the_user_beliefs_and_leaves_the_views_alone(
    store: Store,
) -> None:
    _say(store, 1, Speaker.USER, "i like climbing")
    _say(store, 2, Speaker.COMPANION, VIEW_TEXT)
    user_item: Json = {
        "beliefs": [
            {
                "ref": "m1",
                "quote": "i like climbing",
                "claim": "Likes climbing.",
                "subject": "user",
                "kind": "preference",
                "provenance": "stated",
                "confidence": 0.9,
                "lasting": True,
                "sensitivity": 0,
            }
        ]
    }
    await reflect_once(store, Routed([user_item], [_view("m2", "lazy is a flaw")]), REL)
    view_id = store.self_beliefs(REL)[0].id
    await rebuild(store, Routed([user_item], []), REL)
    assert [b.id for b in store.self_beliefs(REL)] == [view_id]
    assert len(store.user_beliefs(REL)) == 1


class _Talker:
    def __init__(self) -> None:
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply("ok", "m", 5)


def _own_view(bid: str, uid: str, quote: str, claim: str) -> Belief:
    return Belief(
        id=BeliefId(bid),
        relationship_id=REL,
        subject=Subject.SELF,
        kind=BeliefKind.PREFERENCE,
        claim=claim,
        evidence=(Evidence(UtteranceId(uid), quote),),
        provenance=Provenance.COMPANION_SAID,
        speaker=Speaker.COMPANION,
        frame=Frame.REAL,
        confidence=0.6,
        valid_from=T0,
        recorded_at=T0,
    )


async def test_only_approved_views_reach_the_model_and_the_placement_is_logged(
    store: Store, tmp_path: Path
) -> None:
    _say(store, 1, Speaker.COMPANION, "short replies read as more human to me")
    _say(store, 60 * 30, Speaker.COMPANION, "yeah, short replies read as more human, i stand by it")
    _say(store, 3, Speaker.COMPANION, "pineapple on pizza is fine")
    _say(store, 4, Speaker.COMPANION, "i will never pretend to have hands")
    settled_but_unapproved = _own_view(
        "settled",
        "u1",
        "short replies read as more human",
        "The companion thinks short replies read as more human.",
    )
    store.insert_belief(settled_but_unapproved)
    store.add_evidence(
        settled_but_unapproved.id,
        Evidence(UtteranceId(f"u{60 * 30}"), "short replies read as more human"),
    )
    approved_once = _own_view(
        "approved",
        "u3",
        "pineapple on pizza is fine",
        "The companion thinks pineapple on pizza is fine.",
    )
    store.insert_belief(approved_once)
    store.approve_view(approved_once.id, T0)
    closed = _own_view(
        "closed",
        "u4",
        "i will never pretend to have hands",
        "The companion will never pretend to have hands.",
    )
    store.insert_belief(closed)
    store.approve_view(closed.id, T0)
    store.close_belief(closed.id, T0 + timedelta(days=1))
    talker = _Talker()
    await Conversation(store, talker, PREFIX, REL).handle(
        SessionId("s"), "hi", "test", T0 + timedelta(days=3)
    )
    sent = talker.seen[0].messages[-1].content
    assert "[Views of your own that you have expressed and they have approved" in sent
    assert "pineapple on pizza is fine" in sent
    assert "short replies read as more human" not in sent  # settled, but not approved
    assert "pretend to have hands" not in sent  # approved, then closed
    store.close()
    db = tmp_path / "rel.sqlite"
    import sqlite3  # noqa: PLC0415

    with sqlite3.connect(db) as c:
        turn = str(c.execute("SELECT turn_id FROM turn_requests").fetchone()[0])
    report = store_replay.replay_file(db, turn)
    assert report.matched
    reasons = {str(d.belief_id): (d.kind, d.reason) for d in report.decisions if d.belief_id}
    assert reasons["approved"] == (
        DecisionKind.SURFACE,
        "in the card as a view of its own that the user approved",
    )
    assert "settled" not in reasons
    assert "closed" not in reasons
