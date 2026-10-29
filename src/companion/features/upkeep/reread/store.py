"""Judge reads about memories and the owner's answers to what they raise (ADR 0019). Append-only."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from companion.core.types import BeliefId, RelationshipId
from companion.lib.sqlite.db import iso, parse_iso, write_tx


@dataclass(frozen=True, slots=True)
class MemoryCheck:
    id: int
    belief_id: BeliefId
    other_id: BeliefId | None
    reads: tuple[str | None, ...]
    verdict: str
    prompt: str
    at: datetime


def add(  # noqa: PLR0913
    conn: sqlite3.Connection,
    rel: RelationshipId,
    belief_id: BeliefId,
    other_id: BeliefId | None,
    *,
    reads: Sequence[str | None],
    verdict: str,
    prompt: str,
    at: datetime,
) -> int:
    with write_tx(conn):
        cur = conn.execute(
            "INSERT INTO memory_checks"
            " (relationship_id, belief_id, other_id, reads, verdict, prompt, at)"
            " VALUES (?,?,?,?,?,?,?)",
            (rel, belief_id, other_id, json.dumps(list(reads)), verdict, prompt, iso(at)),
        )
    return int(cur.lastrowid or 0)


def checked(
    conn: sqlite3.Connection,
    rel: RelationshipId,
    names: Sequence[str],
    version: str | None = None,
) -> set[BeliefId]:
    """The memories read alone by a prompt, under any of the names it has had, so a renamed prompt
    keeps its history: by any version, or only by `version` (`v3`), so a new version reads them
    again."""
    rows = conn.execute(
        "SELECT DISTINCT belief_id, prompt FROM memory_checks"
        " WHERE relationship_id = ? AND other_id IS NULL",
        (rel,),
    ).fetchall()
    out: set[BeliefId] = set()
    for r in rows:
        name, _, ver = str(r["prompt"]).partition("@")
        if name in names and version in (None, ver):
            out.add(BeliefId(str(r["belief_id"])))
    return out


def unanswered(
    conn: sqlite3.Connection, rel: RelationshipId, verdicts: Sequence[str]
) -> list[MemoryCheck]:
    """Checks with one of these verdicts that the owner has not answered, oldest first."""
    marks = ",".join("?" * len(verdicts))
    rows = conn.execute(
        f"SELECT * FROM memory_checks c WHERE relationship_id = ? AND verdict IN ({marks})"  # noqa: S608
        " AND NOT EXISTS (SELECT 1 FROM memory_answers a WHERE a.check_id = c.id) ORDER BY id",
        (rel, *verdicts),
    ).fetchall()
    return [
        MemoryCheck(
            int(r["id"]),
            BeliefId(str(r["belief_id"])),
            BeliefId(str(r["other_id"])) if r["other_id"] else None,
            tuple(json.loads(str(r["reads"]))),
            str(r["verdict"]),
            str(r["prompt"]),
            parse_iso(str(r["at"])),
        )
        for r in rows
    ]


def answer(conn: sqlite3.Connection, check_id: int, said: str, at: datetime) -> None:
    with write_tx(conn):
        conn.execute(
            "INSERT INTO memory_answers (check_id, answer, at) VALUES (?,?,?)",
            (check_id, said, iso(at)),
        )
