from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
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
from companion.loops.curate import close_duplicates, retire
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
