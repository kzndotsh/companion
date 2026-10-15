from __future__ import annotations

import sqlite3

import pytest

from companion.core.prompt.prefix import build_prefix
from companion.core.replay import TurnRecord
from companion.core.types import Favorite, FavoriteId, SessionId, TurnId
from companion.store.sqlite import favorites, turns
from tests.conftest import REL, T0


def _turn(conn: sqlite3.Connection, tid: str) -> TurnId:
    p = build_prefix("x " * 3000)
    turns.save_prefix(conn, p)
    turns.record_turn(
        conn, TurnRecord(TurnId(tid), REL, SessionId("s"), p.sha256, "", "0" * 64, None, T0)
    )
    return TurnId(tid)


def test_favorites_round_trip_and_are_append_only(conn: sqlite3.Connection) -> None:
    t = _turn(conn, "t1")
    f = Favorite(FavoriteId("f1"), REL, t, "that riff was great", T0)
    favorites.add_favorite(conn, f)
    assert favorites.list_favorites(conn, REL) == [f]
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE favorites SET note = 'x'")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM favorites")


def test_a_favorite_must_point_at_a_real_turn(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        favorites.add_favorite(conn, Favorite(FavoriteId("f"), REL, TurnId("nope"), "", T0))
