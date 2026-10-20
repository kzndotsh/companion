"""The promises the companion made (J12) and what the owner said of them. Append-only."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.promises import Kind, Promise
from companion.core.types import RelationshipId, UtteranceId
from companion.store.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class Recorded:
    promise: Promise
    model: str
    prompt: str
    mark: str | None  # None while current


def add(conn: sqlite3.Connection, p: Promise, *, model: str, prompt: str, at: datetime) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO promises (id, relationship_id, utterance_id, quote, claim, kind, avoid,"
            " at, model, prompt, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                p.id,
                p.relationship_id,
                p.utterance_id,
                p.quote,
                p.claim,
                p.kind,
                p.avoid,
                iso(p.at),
                model,
                prompt,
                iso(at),
            ),
        )


def mark(conn: sqlite3.Connection, promise_id: str, kind: str, reason: str, at: datetime) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO promise_marks (promise_id, mark, reason, at) VALUES (?, ?, ?, ?)",
            (promise_id, kind, reason, iso(at)),
        )


def recorded(conn: sqlite3.Connection, rel: RelationshipId) -> list[Recorded]:
    """Every promise, oldest first, with its newest mark."""
    rows = conn.execute(
        "SELECT p.*, (SELECT m.mark FROM promise_marks m WHERE m.promise_id = p.id"
        " ORDER BY m.id DESC LIMIT 1) AS newest FROM promises p WHERE p.relationship_id = ?"
        " ORDER BY p.at, p.id",
        (rel,),
    ).fetchall()
    return [
        Recorded(
            Promise(
                str(r["id"]),
                RelationshipId(str(r["relationship_id"])),
                UtteranceId(str(r["utterance_id"])),
                str(r["quote"]),
                str(r["claim"]),
                Kind(str(r["kind"])),
                str(r["avoid"]),
                parse_iso(str(r["at"])),
            ),
            str(r["model"]),
            str(r["prompt"]),
            str(r["newest"]) if r["newest"] is not None else None,
        )
        for r in rows
    ]
