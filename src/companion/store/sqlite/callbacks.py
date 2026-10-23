"""Callback verdicts, one per turn, append-only."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.callbacks import Check
from companion.core.types import RelationshipId, TurnId
from companion.lib.sqlite.db import iso, write_tx


@dataclass(frozen=True, slots=True)
class Unchecked:
    turn_id: TurnId
    card: str
    reply: str
    recent: tuple[tuple[str, str], ...]  # (speaker, text), oldest first, ending with their message


def unchecked(conn: sqlite3.Connection, rel: RelationshipId, since: datetime) -> list[Unchecked]:
    """Turns since a time with a card and a reply that no judge has read yet."""
    rows = conn.execute(
        "SELECT t.turn_id, t.card, r.text AS reply, u.at AS at FROM turn_requests t"
        " JOIN utterances r ON r.turn_id = t.turn_id AND r.speaker = 'companion'"
        " JOIN utterances u ON u.turn_id = t.turn_id AND u.speaker = 'user'"
        " WHERE t.relationship_id = ? AND t.card != '' AND u.at >= ?"
        " AND t.turn_id NOT IN (SELECT turn_id FROM callback_checks) ORDER BY u.at",
        (rel, iso(since)),
    ).fetchall()
    out: list[Unchecked] = []
    for r in rows:
        before = conn.execute(
            "SELECT speaker, text FROM utterances WHERE relationship_id = ? AND at <= ?"
            " ORDER BY at DESC LIMIT 7",
            (rel, r["at"]),
        ).fetchall()
        recent = tuple((str(b["speaker"]), str(b["text"])) for b in reversed(before))
        out.append(Unchecked(TurnId(str(r["turn_id"])), str(r["card"]), str(r["reply"]), recent))
    return out


def add(  # noqa: PLR0913, PLR0917
    conn: sqlite3.Connection,
    rel: RelationshipId,
    turn: TurnId,
    check: Check,
    judge: str,
    prompt: str,
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO callback_checks (turn_id, relationship_id, judged_at, judge, prompt,"
            " callback, memories, accurate, fitting, forced) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                turn,
                rel,
                iso(at),
                judge,
                prompt,
                int(check.callback),
                json.dumps(list(check.memories), ensure_ascii=False),
                int(check.accurate),
                int(check.fitting),
                int(check.forced),
            ),
        )


def since(
    conn: sqlite3.Connection, rel: RelationshipId, start: datetime
) -> list[tuple[TurnId, Check]]:
    """Verdicts on turns whose message came at or after a time, oldest first."""
    rows = conn.execute(
        "SELECT c.* FROM callback_checks c JOIN utterances u"
        " ON u.turn_id = c.turn_id AND u.speaker = 'user'"
        " WHERE c.relationship_id = ? AND u.at >= ? ORDER BY u.at",
        (rel, iso(start)),
    ).fetchall()
    return [
        (
            TurnId(str(r["turn_id"])),
            Check(
                bool(r["callback"]),
                tuple(json.loads(str(r["memories"]))),
                bool(r["accurate"]),
                bool(r["fitting"]),
                bool(r["forced"]),
            ),
        )
        for r in rows
    ]
