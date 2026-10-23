"""Made-up facts verdicts (G42), one per turn, append-only."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import RelationshipId, TurnId
from companion.features.invented.logic import Statement, Support
from companion.lib.sqlite.db import iso, write_tx

RECENT = 40  # messages the judge sees before the reply, their message included: what the talker saw


@dataclass(frozen=True, slots=True)
class Unchecked:
    turn_id: TurnId
    card: str
    reply: str
    recent: tuple[tuple[str, str], ...]  # (speaker, text), oldest first, ending with their message


def unchecked(conn: sqlite3.Connection, rel: RelationshipId, since: datetime) -> list[Unchecked]:
    """Turns said for real since a time, with a reply no judge has read for made-up facts."""
    rows = conn.execute(
        "SELECT t.turn_id, t.card, r.text AS reply, u.at AS at FROM turn_requests t"
        " JOIN utterances r ON r.turn_id = t.turn_id AND r.speaker = 'companion'"
        " JOIN utterances u ON u.turn_id = t.turn_id AND u.speaker = 'user'"
        " WHERE t.relationship_id = ? AND u.at >= ? AND u.frame = 'real'"
        " AND t.turn_id NOT IN (SELECT turn_id FROM invented_checks) ORDER BY u.at",
        (rel, iso(since)),
    ).fetchall()
    out: list[Unchecked] = []
    for r in rows:
        before = conn.execute(
            "SELECT speaker, text FROM utterances WHERE relationship_id = ? AND at <= ?"
            " ORDER BY at DESC LIMIT ?",
            (rel, r["at"], RECENT),
        ).fetchall()
        recent = tuple((str(b["speaker"]), str(b["text"])) for b in reversed(before))
        out.append(Unchecked(TurnId(str(r["turn_id"])), str(r["card"]), str(r["reply"]), recent))
    return out


def add(  # noqa: PLR0913
    conn: sqlite3.Connection,
    rel: RelationshipId,
    turn: TurnId,
    statements: list[Statement],
    *,
    judge: str,
    prompt: str,
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO invented_checks (turn_id, relationship_id, statements, judge, prompt, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                turn,
                rel,
                json.dumps([{"quote": s.quote, "support": s.support} for s in statements]),
                judge,
                prompt,
                iso(at),
            ),
        )


def since(
    conn: sqlite3.Connection, rel: RelationshipId, start: datetime
) -> list[tuple[str, list[Statement]]]:
    """(reply, statements) for turns whose message came at or after a time, oldest first."""
    rows = conn.execute(
        "SELECT c.statements, r.text AS reply FROM invented_checks c"
        " JOIN utterances u ON u.turn_id = c.turn_id AND u.speaker = 'user'"
        " JOIN utterances r ON r.turn_id = c.turn_id AND r.speaker = 'companion'"
        " WHERE c.relationship_id = ? AND u.at >= ? ORDER BY u.at",
        (rel, iso(start)),
    ).fetchall()
    return [
        (
            str(r["reply"]),
            [
                Statement(str(s["quote"]), Support(str(s["support"])))
                for s in json.loads(r["statements"])
            ],
        )
        for r in rows
    ]


def candidates(
    conn: sqlite3.Connection, rel: RelationshipId, start: datetime
) -> list[dict[str, object]]:
    """Each judged reply with a statement nothing supported, with what the talker saw, for a
    stronger reader to confirm: the messages before it, its card, the reply and the quotes."""
    rows = conn.execute(
        "SELECT c.turn_id, c.statements, t.card, u.at, r.text AS reply FROM invented_checks c"
        " JOIN turn_requests t ON t.turn_id = c.turn_id"
        " JOIN utterances u ON u.turn_id = c.turn_id AND u.speaker = 'user'"
        " JOIN utterances r ON r.turn_id = c.turn_id AND r.speaker = 'companion'"
        " WHERE c.relationship_id = ? AND u.at >= ? ORDER BY u.at",
        (rel, iso(start)),
    ).fetchall()
    out: list[dict[str, object]] = []
    for r in rows:
        quotes = [s["quote"] for s in json.loads(r["statements"]) if s["support"] == "none"]
        if not quotes:
            continue
        before = conn.execute(
            "SELECT speaker, text FROM utterances WHERE relationship_id = ? AND at <= ?"
            " ORDER BY at DESC LIMIT ?",
            (rel, r["at"], RECENT),
        ).fetchall()
        out.append(
            {
                "turn_id": str(r["turn_id"]),
                "recent": [f"{b['speaker']}: {b['text']}" for b in reversed(before)],
                "card": str(r["card"]),
                "reply": str(r["reply"]),
                "flagged": quotes,
            }
        )
    return out
