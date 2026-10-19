"""Mood effects, append-only (ADR 0016)."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime

from companion.core.mood import PARAMS_VERSION, Effect, Source, State
from companion.core.types import RelationshipId, TurnId
from companion.store.sqlite.db import iso, parse_iso, write_tx


def add(conn: sqlite3.Connection, rel: RelationshipId, effects: Sequence[Effect]) -> None:
    with write_tx(conn):
        conn.executemany(
            "INSERT INTO mood_effects (relationship_id, turn_id, at, state, source, amount,"
            " half_life_hours, params) VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    rel,
                    e.turn,
                    iso(e.at),
                    e.state.value,
                    e.source.value,
                    e.amount,
                    e.half_life_hours,
                    PARAMS_VERSION,
                )
                for e in effects
            ],
        )


def since(conn: sqlite3.Connection, rel: RelationshipId, start: datetime) -> list[Effect]:
    """Effects at or after a time, oldest first. A row naming a state or source this code no longer
    knows is skipped, never guessed."""
    rows = conn.execute(
        "SELECT * FROM mood_effects WHERE relationship_id = ? AND at >= ? ORDER BY at, id",
        (rel, iso(start)),
    ).fetchall()
    known_states = {s.value for s in State}
    known_sources = {s.value for s in Source}
    return [
        Effect(
            State(str(r["state"])),
            Source(str(r["source"])),
            float(r["amount"]),
            float(r["half_life_hours"]),
            parse_iso(str(r["at"])),
            TurnId(str(r["turn_id"])),
        )
        for r in rows
        if r["state"] in known_states and r["source"] in known_sources
    ]
