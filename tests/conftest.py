from __future__ import annotations

import sqlite3
from collections.abc import Callable, Generator
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
from companion.store.sqlite.db import connect, migrate

REL = RelationshipId("rel-1")
T0 = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def conn(tmp_path: Path) -> Generator[sqlite3.Connection]:
    c = connect(tmp_path / "rel.sqlite")
    migrate(c)
    yield c
    c.close()


@pytest.fixture
def utterance() -> Callable[..., Utterance]:
    counter = 0

    def make(
        text: str = "my studio has never been cleaner, which is how I know things are bad",
        speaker: Speaker = Speaker.USER,
        frame: Frame = Frame.REAL,
        uid: str | None = None,
    ) -> Utterance:
        nonlocal counter
        counter += 1
        return Utterance(
            id=UtteranceId(uid or f"u{counter}"),
            relationship_id=REL,
            session_id=SessionId("s1"),
            turn_id=TurnId(f"t{counter}"),
            speaker=speaker,
            text=text,
            frame=frame,
            channel="test",
            at=T0 + timedelta(minutes=counter),
        )

    return make


@pytest.fixture
def belief() -> Callable[..., Belief]:
    def make(
        bid: str = "b1",
        utterance_id: str = "u1",
        quote: str = "my studio has never been cleaner",
        **overrides: object,
    ) -> Belief:
        fields: dict[str, object] = {
            "id": BeliefId(bid),
            "relationship_id": REL,
            "subject": Subject.USER,
            "kind": BeliefKind.TELL,
            "claim": "Cleans the studio obsessively when anxious",
            "evidence": (Evidence(UtteranceId(utterance_id), quote),),
            "provenance": Provenance.STATED,
            "speaker": Speaker.USER,
            "frame": Frame.REAL,
            "confidence": 0.6,
            "valid_from": T0,
            "recorded_at": T0,
        }
        fields.update(overrides)
        return Belief(**fields)  # type: ignore[arg-type]

    return make
