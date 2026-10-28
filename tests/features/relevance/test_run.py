from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import timedelta
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
from companion.core.vectors import Embedded, unit
from companion.features.relevance.logic import SHADOW
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker


class Embedder:
    """Puts a text on the dogs axis when it mentions a dog, on the food axis otherwise."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed(self, texts: Sequence[str]) -> Embedded:
        self.calls.append(list(texts))
        vectors = tuple(unit([1, 0] if "dog" in t.lower() else [0, 1]) for t in texts)
        return Embedded(vectors, "fake-embed", 0.0)


class Picker(Judge):
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        props = schema["properties"]
        if isinstance(props, dict) and set(props) == {"labels"}:
            return Extraction(data={"labels": ["r1"]}, model="j", cost_usd=0.0, latency_ms=1)
        return await super().extract(system, user, schema)


def _belief(store: Store, bid: str, claim: str) -> None:
    said = Utterance(
        UtteranceId(f"u-{bid}"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        claim,
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
            kind=BeliefKind.TRAIT,
            claim=claim,
            evidence=(Evidence(said.id, claim),),
            provenance=Provenance.STATED,
            speaker=Speaker.USER,
            frame=Frame.REAL,
            confidence=0.8,
            valid_from=said.at,
            recorded_at=said.at,
        )
    )


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    _belief(s, "dogs", "The user has two dogs.")
    _belief(s, "food", "The user likes fries.")
    return s


async def _say(store: Store, embedder: Embedder, text: str) -> Talker:
    talker = Talker()
    runtime = Runtime(
        store, talker, PREFIX, REL, judge=Picker(), embedder=embedder, embed_model="fake-embed"
    )
    await handle(runtime, SESSION, text, "test", NOW)
    for _ in range(50):
        await asyncio.sleep(0)
    return talker


def _shadow(store: Store) -> list[dict[str, Json]]:
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=1), 50)}
    return [
        d.detail or {}
        for t in turns
        for d in store.decisions_for_turn(REL, t)
        if d.reason == SHADOW
    ]


async def test_it_logs_the_nearest_and_the_pick_and_sends_nothing(store: Store) -> None:
    embedder = Embedder()
    talker = await _say(store, embedder, "my dog just stole a sock")
    [found] = _shadow(store)
    nearest = found["nearest"]
    assert isinstance(nearest, list)
    assert nearest[0] == {
        "id": "dogs",
        "claim": "The user has two dogs.",
        "on_card": True,
        "score": 1.0,
    }
    assert found["picked"] == [{"id": "dogs", "claim": "The user has two dogs.", "on_card": True}]
    assert "kept in mind" not in talker.seen[0].card
    assert embedder.calls[0] == ["The user has two dogs.", "The user likes fries."]
    assert len(store.belief_embeddings(REL, "fake-embed")) == 2


async def test_memories_are_embedded_once(store: Store) -> None:
    embedder = Embedder()
    await _say(store, embedder, "hi")
    await _say(store, embedder, "hello again")
    assert sum(len(c) == 2 and "The user has two dogs." in c for c in embedder.calls) == 1


async def test_live_it_waits_for_the_pick_and_logs_what_it_was_shown(store: Store) -> None:
    from companion.features.relevance.logic import LIVE  # noqa: PLC0415

    talker = Talker()
    runtime = Runtime(
        store,
        talker,
        PREFIX,
        REL,
        judge=Picker(),
        embedder=Embedder(),
        embed_model="fake-embed",
        relevance="on",
    )
    await handle(runtime, SESSION, "my dog just stole a sock", "test", NOW)
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=1), 50)}
    [live] = [d.detail for t in turns for d in store.decisions_for_turn(REL, t) if d.has_key(LIVE)]
    assert live is not None
    assert live["gated"] is False
    assert not _shadow(store)  # live, not also in shadow
    assert "may bear on what they just said" not in talker.seen[0].card  # already on the card


async def test_with_listening_switched_off_the_live_look_up_does_not_run(store: Store) -> None:
    from companion.features.relevance.logic import LIVE  # noqa: PLC0415

    runtime = Runtime(
        store,
        Talker(),
        PREFIX,
        REL,
        judge=Picker(),
        embedder=Embedder(),
        embed_model="fake-embed",
        relevance="on",
        listen=False,
    )
    await handle(runtime, SESSION, "my dog just stole a sock", "test", NOW)
    turns = {u.turn_id for u in store.history_before(REL, NOW + timedelta(days=1), 50)}
    assert not [d for t in turns for d in store.decisions_for_turn(REL, t) if d.has_key(LIVE)]


def test_a_pick_not_on_the_card_reaches_the_notes(store: Store) -> None:
    from companion.core.types import Frame as F  # noqa: PLC0415
    from companion.kit.current import Turn  # noqa: PLC0415
    from companion.kit.features import Lookups, Moment  # noqa: PLC0415
    from companion.turn.notes import notes_for  # noqa: PLC0415

    runtime = Runtime(store, Talker(), PREFIX, REL)
    t = Turn(SESSION, TurnId("t1"), NOW, [], "fries sound good")
    pick = ((BeliefId("food"), "The user likes fries."),)
    shown = notes_for(
        Moment(runtime, t, F.REAL, None, Lookups(found={"relevant": pick}), False, [])
    )
    assert any("The user likes fries." in line for line in shown.lines)
    hidden = Moment(
        runtime,
        t,
        F.REAL,
        None,
        Lookups(found={"relevant": pick}),
        False,
        [],
        frozenset({BeliefId("food")}),
    )
    assert not any("fries" in line for line in notes_for(hidden).lines)
