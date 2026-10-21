"""Reminders they asked for and what became of each. Append-only; a reminder's state is its newest
event."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.reminders import Kind
from companion.core.types import RelationshipId, TurnId
from companion.store.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class Reminder:
    id: str
    relationship_id: RelationshipId
    kind: Kind
    thing: str
    quote: str
    due_at: datetime
    local_wall: str
    zone: str
    turn_id: TurnId
    created_at: datetime
    state: str = "pending"


def add(conn: sqlite3.Connection, r: Reminder) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO reminders (id, relationship_id, kind, thing, quote, due_at, local_wall,"
            " zone, turn_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                r.id,
                r.relationship_id,
                r.kind,
                r.thing,
                r.quote,
                iso(r.due_at),
                r.local_wall,
                r.zone,
                r.turn_id,
                iso(r.created_at),
            ),
        )
        conn.execute(
            "INSERT INTO reminder_events (reminder_id, state, reason, at)"
            " VALUES (?, 'pending', ?, ?)",
            (r.id, "they asked for it", iso(r.created_at)),
        )


def event(
    conn: sqlite3.Connection, reminder_id: str, state: str, reason: str, at: datetime
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO reminder_events (reminder_id, state, reason, at) VALUES (?, ?, ?, ?)",
            (reminder_id, state, reason, iso(at)),
        )


def claim(conn: sqlite3.Connection, reminder_id: str, at: datetime) -> bool:
    """Mark a pending reminder claimed, in one statement so it is claimed once. False if it was not
    pending any more."""
    with write_tx(conn):
        cur = conn.execute(
            "INSERT INTO reminder_events (reminder_id, state, reason, at)"
            " SELECT ?, 'claimed', 'due, being sent', ? WHERE (SELECT state FROM reminder_events"
            " WHERE reminder_id = ? ORDER BY id DESC LIMIT 1) = 'pending'",
            (reminder_id, iso(at), reminder_id),
        )
    return cur.rowcount == 1


def all_(conn: sqlite3.Connection, rel: RelationshipId) -> list[Reminder]:
    rows = conn.execute(
        "SELECT r.*, (SELECT e.state FROM reminder_events e WHERE e.reminder_id = r.id"
        " ORDER BY e.id DESC LIMIT 1) AS state FROM reminders r WHERE r.relationship_id = ?"
        " ORDER BY r.due_at",
        (rel,),
    ).fetchall()
    return [
        Reminder(
            str(r["id"]),
            RelationshipId(str(r["relationship_id"])),
            Kind(str(r["kind"])),
            str(r["thing"]),
            str(r["quote"]),
            parse_iso(str(r["due_at"])),
            str(r["local_wall"]),
            str(r["zone"]),
            TurnId(str(r["turn_id"])),
            parse_iso(str(r["created_at"])),
            str(r["state"]),
        )
        for r in rows
    ]
