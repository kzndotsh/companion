from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from pathlib import Path

from tests.conftest import REL, T0

from companion.core.lore import Kind, Labelled
from companion.core.types import Belief, Subject, Utterance
from companion.core.vectors import Embedded, unit
from companion.loops.lore import nearest_tastes
from companion.store.sqlite.store import Store

AXIS = {"music": [1.0, 0.0, 0.0], "rain": [0.0, 1.0, 0.0], "advice": [0.0, 0.0, 1.0]}


class Words:
    """Points a text at the axis of the first key word in it."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed(self, texts: Sequence[str]) -> Embedded:
        self.calls.append(list(texts))
        pick = [next((v for k, v in AXIS.items() if k in t), [0.6, 0.6, 0.6]) for t in texts]
        return Embedded(tuple(unit(v) for v in pick), "fake", 0.0)


def test_only_tastes_near_their_message_are_found_and_vectors_are_kept(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    store.append_utterance(utterance(uid="u1"))
    views = {
        "m": ("likes music with piano", Kind.TASTE),
        "r": ("likes rain at night", Kind.TASTE),
        "a": ("gives music advice", Kind.STANCE),
    }
    for bid, (claim, _) in views.items():
        store.insert_belief(belief(bid=bid, subject=Subject.SELF, claim=claim, utterance_id="u1"))
    store.add_view_kinds(
        REL,
        [Labelled(belief(bid=b).id, k) for b, (_, k) in views.items()],
        model="m",
        prompt="p",
        at=T0,
    )
    words = Words()
    found = asyncio.run(nearest_tastes(store, words, REL, "fake", "any music today?", T0))
    assert found is not None
    assert [b.claim for b, _ in found.tastes] == [
        "likes music with piano"
    ]  # rain is below the gate
    asyncio.run(nearest_tastes(store, words, REL, "fake", "rain again", T0))
    assert words.calls[-1] == ["rain again"]  # the tastes' vectors were kept from the first call
