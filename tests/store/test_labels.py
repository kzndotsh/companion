from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from companion.core.types import BeliefId, Depth, Domain, Label
from companion.lib.sqlite.db import connect
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def test_belief_labels_newest_wins_and_append_only(tmp_path: Path) -> None:
    path = tmp_path / "rel.sqlite"
    store = Store(path)
    bid = BeliefId("b1")
    store.add_belief_labels(REL, [Label(bid, Domain.PEOPLE, Depth.SURFACE)], "m", "p@v1", T0)
    store.add_belief_labels(REL, [Label(bid, Domain.HISTORY, Depth.CORE)], "m", "p@v1", T0)
    assert store.belief_labels(REL) == {bid: Label(bid, Domain.HISTORY, Depth.CORE)}
    conn = connect(path)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM belief_labels")
