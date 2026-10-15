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
from companion.loops.curate import approve
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
T0 = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    s.append_utterance(
        Utterance(
            UtteranceId("c1"),
            REL,
            SessionId("s"),
            TurnId("t1"),
            Speaker.COMPANION,
            "i think short replies feel more human",
            Frame.REAL,
            "x",
            T0,
        )
    )
    return s


def _view(bid: str, subject: Subject = Subject.SELF) -> Belief:
    mine = subject is Subject.SELF
    return Belief(
        id=BeliefId(bid),
        relationship_id=REL,
        subject=subject,
        kind=BeliefKind.PREFERENCE,
        claim="The companion thinks short replies feel more human",
        evidence=(Evidence(UtteranceId("c1"), "short replies feel more human"),),
        provenance=Provenance.COMPANION_SAID,
        speaker=Speaker.COMPANION,
        frame=Frame.REAL,
        confidence=0.6,
        valid_from=T0,
        recorded_at=T0 + timedelta(minutes=0 if mine else 1),
    )


def test_approving_a_view_records_it_and_logs_the_decision(store: Store) -> None:
    store.insert_belief(_view("view-1"))
    assert store.approved_views(REL) == set()
    assert approve(store, REL, "view").startswith("approved")
    assert store.approved_views(REL) == {BeliefId("view-1")}
    [d] = store.decisions_for_turn(REL, TurnId("t1"))
    assert "approved by the user" in d.reason


def test_approving_twice_is_harmless(store: Store) -> None:
    store.insert_belief(_view("view-1"))
    approve(store, REL, "view-1")
    approve(store, REL, "view-1")
    assert store.approved_views(REL) == {BeliefId("view-1")}


def test_approval_needs_exactly_one_matching_current_view(store: Store) -> None:
    store.insert_belief(_view("view-1"))
    store.insert_belief(_view("view-2"))
    with pytest.raises(ValueError, match="need exactly one"):
        approve(store, REL, "view")
    with pytest.raises(ValueError, match="need exactly one"):
        approve(store, REL, "nope")


def test_a_belief_about_the_user_cannot_be_approved_as_a_view(store: Store) -> None:
    store.append_utterance(
        Utterance(
            UtteranceId("u1"),
            REL,
            SessionId("s"),
            TurnId("t2"),
            Speaker.USER,
            "i like climbing",
            Frame.REAL,
            "x",
            T0 + timedelta(minutes=1),
        )
    )
    store.insert_belief(
        Belief(
            id=BeliefId("user-1"),
            relationship_id=REL,
            subject=Subject.USER,
            kind=BeliefKind.PREFERENCE,
            claim="Likes climbing",
            evidence=(Evidence(UtteranceId("u1"), "i like climbing"),),
            provenance=Provenance.STATED,
            speaker=Speaker.USER,
            frame=Frame.REAL,
            confidence=0.6,
            valid_from=T0,
            recorded_at=T0,
        )
    )
    with pytest.raises(ValueError, match="need exactly one"):
        approve(store, REL, "user-1")


def test_the_approval_table_is_append_only(store: Store, tmp_path: Path) -> None:
    import sqlite3  # noqa: PLC0415

    store.insert_belief(_view("view-1"))
    approve(store, REL, "view-1")
    store.close()
    with sqlite3.connect(tmp_path / "rel.sqlite") as c:
        with pytest.raises(sqlite3.DatabaseError):
            c.execute("DELETE FROM view_approvals")
        with pytest.raises(sqlite3.DatabaseError):
            c.execute("UPDATE view_approvals SET approved_at = 'x'")
