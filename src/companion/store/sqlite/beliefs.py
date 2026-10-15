"""Bitemporal beliefs. Inserted whole with their evidence; closed by supersession, never deleted."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Evidence,
    Frame,
    Provenance,
    RelationshipId,
    Speaker,
    Subject,
    UtteranceId,
)
from companion.store.sqlite.db import iso, parse_iso, write_tx


def _insert(conn: sqlite3.Connection, b: Belief) -> None:
    conn.execute(
        "INSERT INTO beliefs (id, relationship_id, subject, kind, claim, provenance, speaker,"
        " frame, confidence, sensitivity, valid_from, valid_until, superseded_by, recorded_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            b.id,
            b.relationship_id,
            b.subject,
            b.kind,
            b.claim,
            b.provenance,
            b.speaker,
            b.frame,
            b.confidence,
            b.sensitivity,
            iso(b.valid_from),
            iso(b.valid_until) if b.valid_until else None,
            b.superseded_by,
            iso(b.recorded_at),
        ),
    )
    for e in b.evidence:
        conn.execute(
            "INSERT INTO belief_evidence (belief_id, utterance_id, quote) VALUES (?, ?, ?)",
            (b.id, e.utterance_id, e.quote),
        )


def insert_belief(conn: sqlite3.Connection, b: Belief) -> None:
    with write_tx(conn):
        _insert(conn, b)


def supersede(conn: sqlite3.Connection, old_id: BeliefId, new: Belief, at: datetime) -> None:
    """Close `old` at `at` and point it at `new`, atomically with inserting `new`."""
    with write_tx(conn):
        _insert(conn, new)
        conn.execute(
            "UPDATE beliefs SET valid_until = ?, superseded_by = ? WHERE id = ?",
            (iso(at), new.id, old_id),
        )


def _belief(conn: sqlite3.Connection, row: sqlite3.Row) -> Belief:
    evidence = tuple(
        Evidence(utterance_id=UtteranceId(str(e["utterance_id"])), quote=str(e["quote"]))
        for e in conn.execute(
            "SELECT utterance_id, quote FROM belief_evidence WHERE belief_id = ?"
            " ORDER BY utterance_id, quote",
            (row["id"],),
        )
    )
    until = row["valid_until"]
    sup = row["superseded_by"]
    return Belief(
        id=BeliefId(str(row["id"])),
        relationship_id=RelationshipId(str(row["relationship_id"])),
        subject=Subject(str(row["subject"])),
        kind=BeliefKind(str(row["kind"])),
        claim=str(row["claim"]),
        evidence=evidence,
        provenance=Provenance(str(row["provenance"])),
        speaker=Speaker(str(row["speaker"])),
        frame=Frame(str(row["frame"])),
        confidence=float(row["confidence"]),
        sensitivity=int(row["sensitivity"]),
        valid_from=parse_iso(str(row["valid_from"])),
        valid_until=parse_iso(str(until)) if until is not None else None,
        superseded_by=BeliefId(str(sup)) if sup is not None else None,
        recorded_at=parse_iso(str(row["recorded_at"])),
    )


def get_belief(conn: sqlite3.Connection, belief_id: BeliefId) -> Belief | None:
    row = conn.execute("SELECT * FROM beliefs WHERE id = ?", (belief_id,)).fetchone()
    return _belief(conn, row) if row is not None else None


def current_beliefs(
    conn: sqlite3.Connection, relationship_id: RelationshipId, subject: Subject | None = None
) -> list[Belief]:
    """Who they are now: beliefs that have not been closed."""
    if subject is None:
        rows = conn.execute(
            "SELECT * FROM beliefs WHERE relationship_id = ? AND valid_until IS NULL"
            " ORDER BY valid_from, id",
            (relationship_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM beliefs WHERE relationship_id = ? AND subject = ?"
            " AND valid_until IS NULL ORDER BY valid_from, id",
            (relationship_id, subject),
        ).fetchall()
    return [_belief(conn, r) for r in rows]


def beliefs_without_evidence(conn: sqlite3.Connection) -> list[BeliefId]:
    """Audit query. The schema cannot require a child row, so this is checked after the fact."""
    rows = conn.execute(
        "SELECT b.id FROM beliefs b LEFT JOIN belief_evidence e ON e.belief_id = b.id"
        " WHERE e.belief_id IS NULL"
    ).fetchall()
    return [BeliefId(str(r["id"])) for r in rows]
