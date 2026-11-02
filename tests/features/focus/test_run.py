from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

import pytest

from companion.core.vectors import Embedded
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from tests.features.relevance.test_run import Embedder
from tests.features.relevance.test_run import _belief as belief_in  # pyright: ignore[reportPrivateUsage]
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker


class Broken:
    async def embed(self, texts: Sequence[str]) -> Embedded:
        raise RuntimeError("down")


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    belief_in(s, "food", "The user likes fries.")
    belief_in(s, "dogs", "The user has two dogs.")
    return s


async def _say(store: Store, embedder: object, text: str, focus: str = "on") -> Talker:
    talker = Talker()
    runtime = Runtime(
        store,
        talker,
        PREFIX,
        REL,
        judge=Judge(),
        embedder=embedder,  # type: ignore[arg-type]
        embed_model="fake-embed",
        relevance="off",
        focus=focus,
    )
    await handle(runtime, SESSION, text, "test", NOW)
    for _ in range(50):
        await asyncio.sleep(0)
    return talker


def _order(card: str) -> list[str]:
    return [line for line in card.splitlines() if line.startswith("- The user")]


async def test_the_card_puts_the_memory_closest_to_the_message_first(store: Store) -> None:
    off = await _say(store, Embedder(), "fries for dinner again", focus="off")
    on = await _say(store, Embedder(), "fries for dinner again")
    assert _order(off.seen[0].card)[0].startswith("- The user has two dogs.")
    assert _order(on.seen[0].card)[0].startswith("- The user likes fries.")


async def test_a_failed_look_up_builds_the_card_as_before(store: Store) -> None:
    talker = await _say(store, Broken(), "my dog just stole a sock")
    off = await _say(store, Embedder(), "my dog just stole a sock", focus="off")
    assert _order(talker.seen[0].card) == _order(off.seen[0].card)
