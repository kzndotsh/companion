"""Append-only utterances."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from companion.core.types import (
    Frame,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.store.sqlite.db import iso, parse_iso, write_tx


def _utterance(row: sqlite3.Row) -> Utterance:
    return Utterance(
        id=UtteranceId(str(row["id"])),
        relationship_id=RelationshipId(str(row["relationship_id"])),
        session_id=SessionId(str(row["session_id"])),
        turn_id=TurnId(str(row["turn_id"])),
        speaker=Speaker(str(row["speaker"])),
        text=str(row["text"]),
        frame=Frame(str(row["frame"])),
        channel=str(row["channel"]),
        at=parse_iso(str(row["at"])),
    )


# Replies the user never received are not part of the conversation either side has seen, so the
# queries below skip every utterance that has a row in `undelivered`.


def mark_undelivered(
    conn: sqlite3.Connection,
    relationship_id: RelationshipId,
    text: str,
    reason: str,
    at: datetime,
) -> Utterance | None:
    """Record that the latest companion message with exactly this text was never delivered.
    None when there is no such message (a command's reply, say) or it is already marked."""
    row = conn.execute(
        "SELECT * FROM utterances WHERE relationship_id = ? AND speaker = 'companion' AND text = ?"
        " AND id NOT IN (SELECT utterance_id FROM undelivered)"
        " ORDER BY at DESC, id DESC LIMIT 1",
        (relationship_id, text),
    ).fetchone()
    if row is None:
        return None
    with write_tx(conn):
        conn.execute(
            "INSERT INTO undelivered (utterance_id, relationship_id, reason, at)"
            " VALUES (?, ?, ?, ?)",
            (row["id"], relationship_id, reason, iso(at)),
        )
    return _utterance(row)


def append_utterance(conn: sqlite3.Connection, u: Utterance) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO utterances (id, relationship_id, session_id, turn_id, speaker, text,"
            " frame, channel, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                u.id,
                u.relationship_id,
                u.session_id,
                u.turn_id,
                u.speaker,
                u.text,
                u.frame,
                u.channel,
                iso(u.at),
            ),
        )


def get_utterance(conn: sqlite3.Connection, utterance_id: UtteranceId) -> Utterance | None:
    row = conn.execute("SELECT * FROM utterances WHERE id = ?", (utterance_id,)).fetchone()
    return _utterance(row) if row is not None else None


def session_utterances(
    conn: sqlite3.Connection, relationship_id: RelationshipId, session_id: SessionId
) -> list[Utterance]:
    rows = conn.execute(
        "SELECT * FROM utterances WHERE relationship_id = ? AND session_id = ? ORDER BY at, id",
        (relationship_id, session_id),
    ).fetchall()
    return [_utterance(r) for r in rows]


def history_before(
    conn: sqlite3.Connection, relationship_id: RelationshipId, before: datetime, limit: int
) -> list[Utterance]:
    """The last `limit` utterances strictly before `before`, across sessions, oldest first."""
    rows = conn.execute(
        "SELECT * FROM (SELECT * FROM utterances WHERE relationship_id = ? AND at < ?"
        " AND id NOT IN (SELECT utterance_id FROM undelivered)"
        " ORDER BY at DESC, id DESC LIMIT ?) ORDER BY at, id",
        (relationship_id, iso(before), limit),
    ).fetchall()
    return [_utterance(r) for r in rows]


def user_utterance(
    conn: sqlite3.Connection, relationship_id: RelationshipId, turn_id: TurnId
) -> Utterance | None:
    row = conn.execute(
        "SELECT * FROM utterances WHERE relationship_id = ? AND turn_id = ? AND speaker = 'user'",
        (relationship_id, turn_id),
    ).fetchone()
    return _utterance(row) if row is not None else None


def utterances_after(
    conn: sqlite3.Connection,
    relationship_id: RelationshipId,
    cursor: tuple[datetime, UtteranceId] | None,
    limit: int,
) -> list[Utterance]:
    """Everything after the cursor, oldest first. No cursor means from the beginning."""
    if cursor is None:
        rows = conn.execute(
            "SELECT * FROM utterances WHERE relationship_id = ?"
            " AND id NOT IN (SELECT utterance_id FROM undelivered) ORDER BY at, id LIMIT ?",
            (relationship_id, limit),
        ).fetchall()
    else:
        at = iso(cursor[0])
        rows = conn.execute(
            "SELECT * FROM utterances WHERE relationship_id = ? AND (at > ? OR (at = ? AND id > ?))"
            " AND id NOT IN (SELECT utterance_id FROM undelivered) ORDER BY at, id LIMIT ?",
            (relationship_id, at, at, cursor[1], limit),
        ).fetchall()
    return [_utterance(r) for r in rows]


def companion_utterance(
    conn: sqlite3.Connection, relationship_id: RelationshipId, turn_id: TurnId
) -> Utterance | None:
    row = conn.execute(
        "SELECT * FROM utterances WHERE relationship_id = ? AND turn_id = ?"
        " AND speaker = 'companion' ORDER BY at DESC LIMIT 1",
        (relationship_id, turn_id),
    ).fetchone()
    return _utterance(row) if row is not None else None
