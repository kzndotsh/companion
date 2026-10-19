"""Mood effects, append-only (ADR 0016)."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime

from companion.core.mood import PARAMS_VERSION, Effect, Said, Source, State
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


def said_since(conn: sqlite3.Connection, rel: RelationshipId, start: datetime) -> list[Said]:
    """Their messages since a time, oldest first, with the severity and tone the judges logged."""
    rows = conn.execute(
        "SELECT u.turn_id, u.at, u.text,"
        " (SELECT json_extract(d.detail, '$.labels.severity') FROM decisions d"
        "  WHERE d.relationship_id = u.relationship_id AND d.turn_id = u.turn_id"
        "  AND json_extract(d.detail, '$.prompt') LIKE 'system/listening@%' LIMIT 1) AS severity,"
        " (SELECT json_extract(d.detail, '$.scores.tone') FROM decisions d"
        "  WHERE d.relationship_id = u.relationship_id AND d.turn_id = u.turn_id"
        "  AND json_extract(d.detail, '$.prompt') LIKE 'system/react@%' LIMIT 1) AS tone"
        " FROM utterances u WHERE u.relationship_id = ? AND u.speaker = 'user' AND u.at >= ?"
        " ORDER BY u.at",
        (rel, iso(start)),
    ).fetchall()
    return [
        Said(
            TurnId(str(r["turn_id"])),
            parse_iso(str(r["at"])),
            str(r["text"]),
            None if r["severity"] is None else int(r["severity"]),
            None if r["tone"] is None else str(r["tone"]),
        )
        for r in rows
    ]


def times_since(conn: sqlite3.Connection, rel: RelationshipId, start: datetime) -> list[datetime]:
    """When anything was said, by either side, since a time."""
    rows = conn.execute(
        "SELECT at FROM utterances WHERE relationship_id = ? AND at >= ? ORDER BY at",
        (rel, iso(start)),
    ).fetchall()
    return [parse_iso(str(r["at"])) for r in rows]
