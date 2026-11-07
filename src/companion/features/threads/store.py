"""Threads. Append-only; a thread's state is its newest event. The tables keep their first name,
`open_loops`, from when plans were the only source. Their reach-outs are core storage
(`store/sqlite/reach_outs.py`): every kind of reach-out is read together."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import RelationshipId, UtteranceId, nearest_sensitivity
from companion.features.threads.logic import Source, Thread, ThreadKind, ThreadState
from companion.lib.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class Threads:
    """One relationship file's threads, behind the store's handle (`Store.part`)."""

    conn: sqlite3.Connection

    def add_loop(self, loop: Thread) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO open_loops (id, relationship_id, claim, quote, source_utterance_id,"
                " follow_up_at, sensitivity, created_at, kind, note_only, source)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    loop.source,
                ),
            )
            self.conn.execute(
                "INSERT INTO open_loop_events (loop_id, state, reason, at)"
                " VALUES (?, 'open', ?, ?)",
                (loop.id, "recorded from their own words", iso(loop.created_at)),
            )

    def add_event(self, loop_id: str, state: ThreadState, reason: str, at: datetime) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO open_loop_events (loop_id, state, reason, at) VALUES (?, ?, ?, ?)",
                (loop_id, state, reason, iso(at)),
            )

    def events_with_reason(self, rel: RelationshipId, reason: str) -> dict[str, int]:
        """How many events with this exact reason each loop has."""
        rows = self.conn.execute(
            "SELECT e.loop_id, COUNT(*) AS n FROM open_loop_events e"
            " JOIN open_loops l ON l.id = e.loop_id"
            " WHERE l.relationship_id = ? AND e.reason = ? GROUP BY e.loop_id",
            (rel, reason),
        ).fetchall()
        return {str(r["loop_id"]): int(r["n"]) for r in rows}

    def loops(self, rel: RelationshipId) -> list[Thread]:
        rows = self.conn.execute(
            "SELECT l.*, (SELECT state FROM open_loop_events e WHERE e.loop_id = l.id"
            " ORDER BY e.id DESC LIMIT 1) AS state"
            " FROM open_loops l WHERE l.relationship_id = ? ORDER BY l.follow_up_at, l.id",
            (rel,),
        ).fetchall()
        return [
            Thread(
                id=str(r["id"]),
                relationship_id=RelationshipId(str(r["relationship_id"])),
                claim=str(r["claim"]),
                quote=str(r["quote"]),
                source_utterance_id=UtteranceId(str(r["source_utterance_id"])),
                follow_up_at=parse_iso(str(r["follow_up_at"])),
                sensitivity=nearest_sensitivity(int(r["sensitivity"])),
                created_at=parse_iso(str(r["created_at"])),
                state=ThreadState(str(r["state"])),
                kind=ThreadKind(str(r["kind"])),
                note_only=bool(r["note_only"]),
                source=Source(str(r["source"])),
            )
            for r in rows
        ]

    def record_loop_run(
        self,
        rel: RelationshipId,
        upto: tuple[datetime, UtteranceId],
        *,
        ok: bool,
        reason: str,
        at: datetime,
    ) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO open_loop_runs (relationship_id, upto_at, upto_id, ok, reason, at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (rel, iso(upto[0]), upto[1], int(ok), reason, iso(at)),
            )

    def loop_cursor(self, rel: RelationshipId) -> tuple[datetime, UtteranceId] | None:
        """Where the open-loop pass has read up to: its newest successful run."""
        row = self.conn.execute(
            "SELECT upto_at, upto_id FROM open_loop_runs WHERE relationship_id = ? AND ok = 1"
            " ORDER BY id DESC LIMIT 1",
            (rel,),
        ).fetchone()
        return (
            None
            if row is None
            else (parse_iso(str(row["upto_at"])), UtteranceId(str(row["upto_id"])))
        )

    def failed_tries(self, rel: RelationshipId, upto_id: UtteranceId) -> int:
        """Failed tries at the batch ending here since the bookmark last moved."""
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM open_loop_runs WHERE relationship_id = ? AND ok = 0"
            " AND upto_id = ? AND id > COALESCE((SELECT MAX(id) FROM open_loop_runs"
            " WHERE relationship_id = ? AND ok = 1), 0)",
            (rel, upto_id, rel),
        ).fetchone()
        return int(row["n"])
