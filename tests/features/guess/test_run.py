from __future__ import annotations

from datetime import datetime, timedelta
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
    Speaker,
    Subject,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.basics.logic import name_belief
from companion.features.guess.logic import INVITED
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker


class Guesser(Judge):
    """Reads ordinary turns; says every short question invites a guess about what it is time for,
    and the recall look-up picks the first memory it is shown."""

    def __init__(self, severity: int = 0, *, invited: bool = True) -> None:
        super().__init__(severity)
        self.invited, self.asked = invited, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        props = schema["properties"]
        if isinstance(props, dict) and set(props) == {"invited", "about"}:
            self.asked += 1
            data: Json = {"invited": self.invited, "about": "what it is time for them"}
            return Extraction(data, "j", 0.0, 1)
        if isinstance(props, dict) and set(props) == {"labels"}:
            return Extraction({"labels": ["r1"]}, "j", 0.0, 1)
        return await super().extract(system, user, schema)


def _remember(store: Store, bid: str, text: str, claim: str, sensitivity: int = 0) -> None:
    said = Utterance(
        UtteranceId(f"u-{bid}"),
        REL,
        SESSION,
        TurnId(f"t-{bid}"),
        Speaker.USER,
        text,
        Frame.REAL,
        "test",
        NOW - timedelta(days=1),
    )
    store.append_utterance(said)
    store.insert_belief(
        Belief(
            id=BeliefId(bid),
            relationship_id=REL,
            subject=Subject.USER,
            kind=BeliefKind.PREFERENCE,
            claim=claim,
            evidence=(Evidence(said.id, text),),
            provenance=Provenance.STATED,
            speaker=Speaker.USER,
            frame=Frame.REAL,
            confidence=0.8,
            valid_from=said.at,
            recorded_at=said.at,
            sensitivity=sensitivity,
        )
    )


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    _remember(s, "secret", "a private thing", "The user has a private worry.", sensitivity=2)
    _remember(s, "coffee", "coffee is my ritual", "The user loves the ritual of coffee.")
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "sam",
        Frame.REAL,
        "t",
        NOW - timedelta(days=2),
    )
    s.append_utterance(said)
    s.insert_belief(name_belief(said, "Sam", "b-name", said.at))
    return s


async def _say(store: Store, judge: Guesser, text: str, at: datetime = NOW) -> str:
    talker = Talker()
    await handle(Runtime(store, talker, PREFIX, REL, judge=judge), SESSION, text, "t", at)
    return talker.seen[0].card


async def test_an_invited_guess_offers_a_memory_and_never_a_sensitive_one(store: Store) -> None:
    card = await _say(store, Guesser(), "you know what time it is?")
    assert "inviting you to guess what it is time for them" in card
    assert "The user loves the ritual of coffee." in card
    assert "private worry" not in card
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=1), 50)}
    logged = [d for t in turns for d in store.decisions_for_turn(REL, t) if d.reason == INVITED]
    assert len(logged) == 1


async def test_no_invitation_no_question_or_a_serious_turn_gets_no_guess(store: Store) -> None:
    assert "inviting you to guess" not in await _say(
        store, Guesser(invited=False), "what time is it?"
    )
    judge = Guesser()
    assert "inviting you to guess" not in await _say(store, judge, "ok coffee time lol")
    assert judge.asked == 0  # not a question: the judge is never asked
    assert "inviting you to guess" not in await _say(
        store, Guesser(severity=2), "you know what day it is?"
    )
