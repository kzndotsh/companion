"""Open loops and the reach-outs about them. Append-only; a loop's state is its newest event."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.openloops import LoopKind, LoopState, OpenLoop
from companion.core.types import RelationshipId, UtteranceId
from companion.store.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class ReachOut:
    id: str
    relationship_id: RelationshipId
    loop_id: str
    mode: str  # "shadow" (drafted, never sent) or "live"
    draft: str
    reason: str
    at: datetime


def add_loop(conn: sqlite3.Connection, loop: OpenLoop) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO open_loops (id, relationship_id, claim, quote, source_utterance_id,"
            " follow_up_at, sensitivity, created_at, kind, note_only)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                loop.id,
                loop.relationship_id,
                loop.claim,
                loop.quote,
                loop.source_utterance_id,
                iso(loop.follow_up_at),
                loop.sensitivity,
                iso(loop.created_at),
                loop.kind,
                int(loop.note_only),
            ),
        )
        conn.execute(
            "INSERT INTO open_loop_events (loop_id, state, reason, at) VALUES (?, 'open', ?, ?)",
            (loop.id, "recorded from their own words", iso(loop.created_at)),
        )


def add_event(
    conn: sqlite3.Connection, loop_id: str, state: LoopState, reason: str, at: datetime
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO open_loop_events (loop_id, state, reason, at) VALUES (?, ?, ?, ?)",
            (loop_id, state, reason, iso(at)),
        )


def events_with_reason(
    conn: sqlite3.Connection, rel: RelationshipId, reason: str
) -> dict[str, int]:
    """How many events with this exact reason each loop has."""
    rows = conn.execute(
        "SELECT e.loop_id, COUNT(*) AS n FROM open_loop_events e"
        " JOIN open_loops l ON l.id = e.loop_id"
        " WHERE l.relationship_id = ? AND e.reason = ? GROUP BY e.loop_id",
        (rel, reason),
    ).fetchall()
    return {str(r["loop_id"]): int(r["n"]) for r in rows}


def loops(conn: sqlite3.Connection, rel: RelationshipId) -> list[OpenLoop]:
    rows = conn.execute(
        "SELECT l.*, (SELECT state FROM open_loop_events e WHERE e.loop_id = l.id"
        " ORDER BY e.id DESC LIMIT 1) AS state"
        " FROM open_loops l WHERE l.relationship_id = ? ORDER BY l.follow_up_at, l.id",
        (rel,),
    ).fetchall()
    return [
        OpenLoop(
            id=str(r["id"]),
            relationship_id=RelationshipId(str(r["relationship_id"])),
            claim=str(r["claim"]),
            quote=str(r["quote"]),
            source_utterance_id=UtteranceId(str(r["source_utterance_id"])),
            follow_up_at=parse_iso(str(r["follow_up_at"])),
            sensitivity=int(r["sensitivity"]),
            created_at=parse_iso(str(r["created_at"])),
            state=LoopState(str(r["state"])),
            kind=LoopKind(str(r["kind"])),
            note_only=bool(r["note_only"]),
        )
        for r in rows
    ]


def add_reach_out(conn: sqlite3.Connection, r: ReachOut) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO reach_outs (id, relationship_id, loop_id, mode, draft, reason, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r.id, r.relationship_id, r.loop_id, r.mode, r.draft, r.reason, iso(r.at)),
        )


def reach_outs_since(
    conn: sqlite3.Connection, rel: RelationshipId, since: datetime | None = None
) -> list[ReachOut]:
    rows = conn.execute(
        "SELECT * FROM reach_outs WHERE relationship_id = ? AND at >= ? ORDER BY at, id",
        (rel, iso(since) if since else ""),
    ).fetchall()
    return [
        ReachOut(
            str(r["id"]),
            RelationshipId(str(r["relationship_id"])),
            str(r["loop_id"]),
            str(r["mode"]),
            str(r["draft"]),
            str(r["reason"]),
            parse_iso(str(r["at"])),
        )
        for r in rows
    ]


def record_loop_run(  # noqa: PLR0913
    conn: sqlite3.Connection,
    rel: RelationshipId,
    upto: tuple[datetime, UtteranceId],
    *,
    ok: bool,
    reason: str,
    at: datetime,
) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO open_loop_runs (relationship_id, upto_at, upto_id, ok, reason, at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (rel, iso(upto[0]), upto[1], int(ok), reason, iso(at)),
        )


def loop_cursor(
    conn: sqlite3.Connection, rel: RelationshipId
) -> tuple[datetime, UtteranceId] | None:
    """Where the open-loop pass has read up to: its newest successful run."""
    row = conn.execute(
        "SELECT upto_at, upto_id FROM open_loop_runs WHERE relationship_id = ? AND ok = 1"
        " ORDER BY id DESC LIMIT 1",
        (rel,),
    ).fetchone()
    return (
        None if row is None else (parse_iso(str(row["upto_at"])), UtteranceId(str(row["upto_id"])))
    )


def failed_tries(conn: sqlite3.Connection, rel: RelationshipId, upto_id: UtteranceId) -> int:
    """Failed tries at the batch ending here since the bookmark last moved."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM open_loop_runs WHERE relationship_id = ? AND ok = 0"
        " AND upto_id = ? AND id > COALESCE((SELECT MAX(id) FROM open_loop_runs"
        " WHERE relationship_id = ? AND ok = 1), 0)",
        (rel, upto_id, rel),
    ).fetchone()
    return int(row["n"])
