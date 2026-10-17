from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from companion.cli import spend as spend_cli
from companion.core.spend import SpendEvent
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rel.sqlite")
    for i, (purpose, cost) in enumerate(
        [("talker", 0.002), ("talker", 0.003), ("ack", 0.0004), ("memory", 0.001)]
    ):
        store.record_spend(REL, SpendEvent(purpose, "m", cost, 100), T0 + timedelta(minutes=i))
    return store


def test_spend_is_summed_by_purpose_and_model_biggest_first(tmp_path: Path) -> None:
    store = _store(tmp_path)
    rows = store.spend_since(REL, T0)
    assert [(p, n) for p, _, n, _ in rows] == [("talker", 2), ("memory", 1), ("ack", 1)]
    assert rows[0][3] == pytest.approx(0.005)


def test_only_spend_since_the_given_time_counts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    rows = store.spend_since(REL, T0 + timedelta(minutes=2))
    assert sum(r[3] for r in rows) == pytest.approx(0.0014)


def test_spend_cannot_be_edited_or_deleted(tmp_path: Path) -> None:
    store = _store(tmp_path)
    conn = sqlite3.connect(tmp_path / "rel.sqlite")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM spend")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE spend SET cost_usd = 0")
    conn.close()
    store.close()


def test_the_report_names_today_and_the_week(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.close()
    out = spend_cli.run(tmp_path / "rel.sqlite", str(REL), now=T0 + timedelta(minutes=10))
    assert "today: $0.0064 over 4 calls" in out
    assert "last 7 days" in out
    assert "talker" in out


def test_an_empty_ledger_says_so(tmp_path: Path) -> None:
    Store(tmp_path / "rel.sqlite").close()
    assert spend_cli.run(tmp_path / "rel.sqlite", str(REL)) == "no spend recorded yet\n"
