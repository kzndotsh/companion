from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from companion.core.relevance import unit
from companion.core.types import BeliefId
from companion.store.sqlite.db import connect
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def test_vectors_read_back_per_model_newest_wins(tmp_path: Path) -> None:
    store = Store(tmp_path / "rel.sqlite")
    bid = BeliefId("b1")
    store.add_belief_embeddings(REL, {bid: unit([3, 4])}, "m1", T0)
    store.add_belief_embeddings(REL, {bid: unit([0, 1])}, "m1", T0)
    store.add_belief_embeddings(REL, {bid: unit([1, 0])}, "m2", T0)
    assert store.belief_embeddings(REL, "m1") == {bid: (0.0, 1.0)}
    assert store.belief_embeddings(REL, "m2") == {bid: (1.0, 0.0)}
    assert store.belief_embeddings(REL, "m3") == {}


def test_the_table_is_append_only(tmp_path: Path) -> None:
    path = tmp_path / "rel.sqlite"
    Store(path).add_belief_embeddings(REL, {BeliefId("b1"): unit([1, 0])}, "m", T0)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connect(path).execute("DELETE FROM belief_embeddings")
