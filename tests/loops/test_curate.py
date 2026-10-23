from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
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
from companion.loops.curate import close_duplicates, merge, retire
from companion.memory.rebuild import rebuild
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
T0 = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
TEXT = "i hate cooking, im so lazy lol and i'm lactose intolerant"


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    s.append_utterance(
        Utterance(
            UtteranceId("u1"),
            REL,
            SessionId("s"),
            TurnId("t1"),
            Speaker.USER,
            TEXT,
            Frame.REAL,
            "test",
            T0,
        )
    )
    return s


def _belief(bid: str, claim: str, quote: str, minutes: int) -> Belief:
    return Belief(
        id=BeliefId(bid),
        relationship_id=REL,
        subject=Subject.USER,
        kind=BeliefKind.PREFERENCE,
        claim=claim,
        evidence=(Evidence(UtteranceId("u1"), quote),),
        provenance=Provenance.STATED,
        speaker=Speaker.USER,
        frame=Frame.REAL,
        confidence=0.6,
        valid_from=T0,
        recorded_at=T0 + timedelta(minutes=minutes),
    )


def test_duplicates_close_to_the_fullest_claim(store: Store) -> None:
    store.insert_belief(_belief("b1", "User hates cooking.", "i hate cooking", 1))
    store.insert_belief(
        _belief(
            "b2",
            "User hates cooking and calls themselves lazy about it.",
            "i hate cooking, im so lazy",
            2,
        )
    )
    store.insert_belief(_belief("b3", "User is lactose intolerant.", "i'm lactose intolerant", 3))
    report = close_duplicates(store, REL)
    assert len(report) == 1
    claims = {b.claim for b in store.current_beliefs(REL)}
    assert claims == {
        "User hates cooking and calls themselves lazy about it.",
        "User is lactose intolerant.",
    }


def test_closing_keeps_the_row_and_logs_why(store: Store) -> None:
    store.insert_belief(_belief("b1", "User hates cooking.", "i hate cooking", 1))
    store.insert_belief(_belief("b2", "User hates cooking, lazy.", "i hate cooking, im so lazy", 2))
    close_duplicates(store, REL)
    assert [b.id for b in store.current_beliefs(REL)] == ["b2"]


def test_retire_needs_exactly_one_match(store: Store) -> None:
    store.insert_belief(_belief("bx1", "A.", "i hate cooking", 1))
    store.insert_belief(_belief("bx2", "B.", "i'm lactose intolerant", 2))
    with pytest.raises(ValueError, match="need exactly one"):
        retire(store, REL, "bx", "x")
    assert retire(store, REL, "bx1", "noise").startswith("closed")
    assert [b.id for b in store.current_beliefs(REL)] == ["bx2"]


class _Ex:
    def __init__(self, *responses: Json, fail_on: int | None = None) -> None:
        self.responses = list(responses)
        self.calls = 0
        self.fail_on = fail_on

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        self.calls += 1
        if self.fail_on == self.calls:
            msg = "provider down"
            raise RuntimeError(msg)
        return Extraction(data=self.responses.pop(0), model="fake", cost_usd=0.0, latency_ms=1)


def _item(claim: str, quote: str) -> dict[str, Json]:
    return {
        "ref": "m1",
        "quote": quote,
        "claim": claim,
        "subject": "user",
        "kind": "preference",
        "provenance": "stated",
        "confidence": 0.9,
        "lasting": True,
        "sensitivity": 0,
    }


async def test_rebuild_restates_beliefs_and_closes_the_old_ones(store: Store) -> None:
    store.insert_belief(_belief("old", "User hates it.", "i hate cooking", 1))
    ex = _Ex({"beliefs": [_item("The user hates cooking, as of 2026-10-15.", "i hate cooking")]})
    report = await rebuild(store, ex, REL)
    assert "1 beliefs added, 1 replaced" in report
    assert [b.claim for b in store.current_beliefs(REL)] == [
        "The user hates cooking, as of 2026-10-15."
    ]


async def test_a_failed_rebuild_leaves_the_old_beliefs_in_force(store: Store) -> None:
    store.insert_belief(_belief("old", "User hates it.", "i hate cooking", 1))
    with pytest.raises(RuntimeError):
        await rebuild(store, _Ex(fail_on=1), REL)
    assert [b.id for b in store.current_beliefs(REL)] == ["old"]


def test_merge_keeps_every_quote_and_closes_the_originals(store: Store) -> None:
    store.insert_belief(_belief("m1", "Hates cooking.", "i hate cooking", 1))
    store.insert_belief(_belief("m2", "Feels lazy.", "im so lazy lol", 2))
    said = merge(store, REL, ["m1", "m2"], "The user hates cooking and calls themselves lazy.")
    assert said.startswith("merged 2 into")
    [now] = store.current_beliefs(REL)
    assert now.claim == "The user hates cooking and calls themselves lazy."
    assert {e.quote for e in now.evidence} == {"i hate cooking", "im so lazy lol"}
    with pytest.raises(ValueError, match="two or more"):
        merge(store, REL, [now.id], "x")
