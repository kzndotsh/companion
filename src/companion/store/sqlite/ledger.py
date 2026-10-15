"""Append-only utterances."""

from __future__ import annotations

import sqlite3

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
