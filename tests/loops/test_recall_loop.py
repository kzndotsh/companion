from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.recall import candidates, parse, recall_note
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
from companion.loops.fast import Conversation
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SESSION = SessionId("s")
NOW = datetime(2026, 10, 18, 17, 0, tzinfo=UTC)
PREFIX = build_prefix("You are a companion. " * 300)
SAID = Utterance(
    UtteranceId("u0"),
    REL,
    SESSION,
    TurnId("t0"),
    Speaker.USER,
    "i always want a burger lol",
    Frame.REAL,
    "test",
    datetime(2026, 10, 16, 12, 0, tzinfo=UTC),
)


def _belief(bid: str, claim: str, quote: str, sens: int = 0) -> Belief:
    return Belief(
        id=BeliefId(bid),
        relationship_id=REL,
        subject=Subject.USER,
        kind=BeliefKind.PREFERENCE,
        claim=claim,
        evidence=(Evidence(SAID.id, quote),),
        provenance=Provenance.STATED,
        speaker=Speaker.USER,
        frame=Frame.REAL,
        confidence=0.7,
        valid_from=SAID.at,
        recorded_at=SAID.at,
        sensitivity=sens,
    )


class Talker:
    def __init__(self) -> None:
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply(text="burger, obviously", model="fake", latency_ms=1)


class Judge:
    """Labels every message as a request to remember 'favorite food', and picks the given labels."""

    def __init__(self, picks: list[str], *, recall: bool = True, fail: bool = False) -> None:
        self.picks, self.recall, self.fail = picks, recall, fail

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user
        props = schema["properties"]
        assert isinstance(props, dict)
        if "severity" in props:
            data: Json = {
                "severity": 0,
                "stance": "other",
                "vague": False,
                "medical": False,
                "rude": False,
                "recall": self.recall,
                "topic": "favorite food" if self.recall else "",
            }
        elif "labels" in props:
            if self.fail:
                msg = "provider down"
                raise RuntimeError(msg)
            data = {"labels": list(self.picks)}
        else:
            data = None
        return Extraction(data=data, model="j", cost_usd=0.0, latency_ms=1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    s.append_utterance(SAID)
    s.insert_belief(_belief("b1", "The user always wants a burger.", "i always want a burger"))
    return s


async def _ask(store: Store, judge: Judge) -> Talker:
    talker = Talker()
    convo = Conversation(store, talker, PREFIX, REL, judge=judge)
    await convo.handle(SESSION, "come on, you know this one", "test", NOW)
    return talker


async def test_what_they_asked_it_to_remember_is_looked_up_and_shown_that_turn(
    store: Store,
) -> None:
    talker = await _ask(store, Judge(["r1"]))
    card = talker.seen[0].card
    assert "They asked you to remember this" in card
    assert "- The user always wants a burger." in card
    assert "remember" not in talker.seen[0].messages[-1].content.replace("you know this one", "")


@pytest.mark.parametrize(
    ("judge", "why"),
    [
        (Judge([], recall=False), "not asked"),
        (Judge(["r9"]), "unknown label"),
        (Judge(["r1"], fail=True), "look-up failed"),
    ],
)
async def test_nothing_is_added_when_not_asked_unfound_or_failed(
    store: Store, judge: Judge, why: str
) -> None:
    talker = await _ask(store, judge)
    assert "They asked you to remember this" not in talker.seen[0].card, why


async def test_the_look_up_is_logged_with_the_topic_and_what_it_found(store: Store) -> None:
    await _ask(store, Judge(["r1"]))
    [turn] = {u.turn_id for u in store.history_before(REL, NOW.replace(hour=23), 5)} - {"t0"}
    found = [d for d in store.decisions_for_turn(REL, turn) if d.reason.startswith("recall:")]
    assert [d.reason for d in found] == ["recall: they asked about 'favorite food'; 1 found"]
    assert found[0].detail is not None
    assert found[0].detail["picked"] == ["b1"]


def test_only_stated_beliefs_below_crisis_level_are_candidates_and_picks_are_capped() -> None:
    labelled = candidates([_belief(f"b{i}", f"claim {i}", "burger") for i in range(8)])
    assert len(labelled) == 8
    assert candidates([_belief("x", "in crisis", "burger", sens=3)]) == {}
    picked = parse({"labels": [*labelled, "r1", "nope"]}, labelled)
    assert len(picked) == 5
    assert recall_note([]) is None


def test_a_label_written_the_way_the_list_shows_it_is_still_read() -> None:
    labelled = candidates([_belief("b1", "The user always wants a burger.", "burger")])
    assert [b.id for b in parse({"labels": ["[r1]", " r1 "]}, labelled)] == ["b1"]
