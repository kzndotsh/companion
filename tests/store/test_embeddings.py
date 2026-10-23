from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from companion.core.types import Belief, BeliefId, Utterance
from companion.core.vectors import unit
from companion.lib.sqlite.db import connect
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def _current(
    store: Store, utterance: Callable[..., Utterance], belief: Callable[..., Belief], *ids: str
) -> None:
    store.append_utterance(utterance(text="hi", uid="u1"))
    for bid in ids:
        store.insert_belief(belief(bid=bid, utterance_id="u1", quote="hi", claim=f"claim {bid}"))


def test_vectors_read_back_per_model_newest_wins(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    _current(store, utterance, belief, "b1")
    bid = BeliefId("b1")
    store.add_belief_embeddings(REL, {bid: unit([3, 4])}, "m1", T0)
    store.add_belief_embeddings(REL, {bid: unit([0, 1])}, "m1", T0)
    store.add_belief_embeddings(REL, {bid: unit([1, 0])}, "m2", T0)
    assert store.belief_embeddings(REL, "m1") == {bid: (0.0, 1.0)}
    assert store.belief_embeddings(REL, "m2") == {bid: (1.0, 0.0)}
    assert store.belief_embeddings(REL, "m3") == {}


def test_a_closed_beliefs_vector_stays_stored_but_is_not_loaded(
    tmp_path: Path, utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    _current(store, utterance, belief, "open", "closed")
    store.add_belief_embeddings(
        REL, {BeliefId("open"): unit([1, 0]), BeliefId("closed"): unit([0, 1])}, "m", T0
    )
    store.close_belief(BeliefId("closed"), T0)
    assert set(store.belief_embeddings(REL, "m")) == {"open"}


def test_the_table_is_append_only(tmp_path: Path) -> None:
    path = tmp_path / "rel.sqlite"
    Store(path).add_belief_embeddings(REL, {BeliefId("b1"): unit([1, 0])}, "m", T0)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connect(path).execute("DELETE FROM belief_embeddings")
