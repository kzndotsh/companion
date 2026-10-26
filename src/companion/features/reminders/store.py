"""Reminders they asked for, the series a repeating one belongs to, and what became of each.
Append-only; a reminder's or a series' state is its newest event."""

from __future__ import annotations

import sqlite3
from datetime import datetime, time

from companion.core.types import RelationshipId, TurnId
from companion.features.reminders.logic import Kind, Part, Reminder, Repeat, Series, Standing
from companion.lib.sqlite.db import iso, parse_iso, write_tx

_INSERT = (
    "INSERT {verb} INTO reminders (id, relationship_id, kind, thing, quote, due_at, local_wall,"
    " zone, turn_id, created_at, series_id, seq) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _row(r: Reminder) -> tuple[object, ...]:
    return (
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
        r.series_id,
        r.seq,
    )


def _pending(conn: sqlite3.Connection, r: Reminder, reason: str) -> None:
    conn.execute(
        "INSERT INTO reminder_events (reminder_id, state, reason, at) VALUES (?, 'pending', ?, ?)",
        (r.id, reason, iso(r.created_at)),
    )


def add(conn: sqlite3.Connection, r: Reminder) -> None:
    with write_tx(conn):
        conn.execute(_INSERT.format(verb=""), _row(r))
        _pending(conn, r, "they asked for it")


def add_occurrence(conn: sqlite3.Connection, r: Reminder) -> bool:
    """Make occurrence `r.seq` of its series, pending. False, and nothing written, when that number
    was already made: scheduling twice makes one."""
    with write_tx(conn):
        cur = conn.execute(_INSERT.format(verb="OR IGNORE"), _row(r))
        if cur.rowcount == 1:
            _pending(conn, r, f"number {r.seq} of its series")
    return cur.rowcount == 1


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
        "SELECT r.*, e.state, e.at AS state_at FROM reminders r JOIN reminder_events e"
        " ON e.id = (SELECT MAX(id) FROM reminder_events WHERE reminder_id = r.id)"
        " WHERE r.relationship_id = ? ORDER BY r.due_at",
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
            None if r["series_id"] is None else str(r["series_id"]),
            None if r["seq"] is None else int(r["seq"]),
            parse_iso(str(r["state_at"])),
        )
        for r in rows
    ]


def add_series(conn: sqlite3.Connection, s: Series) -> None:
    at = s.repeat.at
    with write_tx(conn):
        conn.execute(
            "INSERT INTO series (id, relationship_id, kind, thing, quote, rule, weekday, hour,"
            " minute, part, zone, turn_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                s.id,
                s.relationship_id,
                s.kind,
                s.thing,
                s.quote,
                s.repeat.rule,
                s.repeat.weekday,
                None if at is None else at.hour,
                None if at is None else at.minute,
                s.repeat.part,
                s.zone,
                s.turn_id,
                iso(s.created_at),
            ),
        )
        conn.execute(
            "INSERT INTO series_events (series_id, state, reason, at) VALUES (?, 'active', ?, ?)",
            (s.id, "they asked for it", iso(s.created_at)),
        )


def series_event(
    conn: sqlite3.Connection, series_id: str, state: Standing, reason: str, at: datetime
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO series_events (series_id, state, reason, at) VALUES (?, ?, ?, ?)",
            (series_id, state, reason, iso(at)),
        )


def all_series(conn: sqlite3.Connection, rel: RelationshipId) -> list[Series]:
    rows = conn.execute(
        "SELECT s.*, (SELECT e.state FROM series_events e WHERE e.series_id = s.id"
        " ORDER BY e.id DESC LIMIT 1) AS state FROM series s WHERE s.relationship_id = ?"
        " ORDER BY s.created_at",
        (rel,),
    ).fetchall()
    return [
        Series(
            str(r["id"]),
            RelationshipId(str(r["relationship_id"])),
            Kind(str(r["kind"])),
            str(r["thing"]),
            str(r["quote"]),
            Repeat(
                None if r["weekday"] is None else int(r["weekday"]),
                None if r["hour"] is None else time(int(r["hour"]), int(r["minute"])),
                Part(str(r["part"])),
            ),
            str(r["zone"]),
            TurnId(str(r["turn_id"])),
            parse_iso(str(r["created_at"])),
            Standing(str(r["state"])),
        )
        for r in rows
    ]


def their_times(conn: sqlite3.Connection, rel: RelationshipId, since: datetime) -> list[datetime]:
    """When they wrote, oldest first: what a learned time, a skip and a pause are read from."""
    rows = conn.execute(
        "SELECT at FROM utterances WHERE relationship_id = ? AND speaker = 'user' AND at >= ?"
        " ORDER BY at",
        (rel, iso(since)),
    ).fetchall()
    return [parse_iso(str(r["at"])) for r in rows]
