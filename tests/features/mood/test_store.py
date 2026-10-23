from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from companion.core.types import TurnId
from companion.features.mood.logic import Source, effect
from companion.lib.sqlite.db import connect, iso
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


def test_effects_read_back_exactly_and_oldest_first(tmp_path: Path) -> None:
    store = Store(tmp_path / "rel.sqlite")
    later = effect(Source.TONE_FUNNY, 0.4, T0 + timedelta(minutes=5), TurnId("t2"))
    first = effect(Source.SERIOUS, 0.8, T0, TurnId("t1"))
    store.add_mood_effects(REL, [later, first])
    assert store.mood_effects_since(REL, T0) == [first, later]
    assert store.mood_effects_since(REL, T0 + timedelta(minutes=1)) == [later]


@pytest.mark.parametrize("sql", ["UPDATE mood_effects SET amount = 0", "DELETE FROM mood_effects"])
def test_the_table_is_append_only(tmp_path: Path, sql: str) -> None:
    path = tmp_path / "rel.sqlite"
    Store(path).add_mood_effects(REL, [effect(Source.SERIOUS, 0.8, T0, TurnId("t1"))])
    conn = connect(path)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute(sql)


def test_a_row_this_code_does_not_know_is_skipped_not_guessed(tmp_path: Path) -> None:
    path = tmp_path / "rel.sqlite"
    store = Store(path)
    store.add_mood_effects(REL, [effect(Source.SERIOUS, 0.8, T0, TurnId("t1"))])
    conn = connect(path)
    with conn:
        conn.execute(
            "INSERT INTO mood_effects (relationship_id, turn_id, at, state, source, amount,"
            " half_life_hours, params) VALUES (?, 't0', ?, 'buzzing', 'energy', 0.3, 2, '0')",
            (REL, iso(T0)),
        )
    assert [e.source for e in store.mood_effects_since(REL, T0)] == [Source.SERIOUS]
