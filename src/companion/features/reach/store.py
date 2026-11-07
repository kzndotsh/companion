"""Its own reach-outs (ADR 0021): would-sends in shadow, sends when live, and dropped drafts.
Append-only (`store/sqlite/migrations/0032_own_reach_outs.sql`)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Container
from dataclasses import dataclass
from datetime import datetime

from companion.core.reachout import WOULD_NUDGE, Kind, Mode, ReachRecord
from companion.core.types import Json, RelationshipId
from companion.lib.sqlite.db import iso, parse_iso, write_tx
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Own:
    id: str
    relationship_id: RelationshipId
    kind: Kind
    thing: str  # the one thing it is about, its id and text, or empty
    draft: str
    mode: Mode
    detail: dict[str, Json]  # the rhythm, the share, the dial and why
    at: datetime


@dataclass(frozen=True, slots=True)
class Reaches:
    """One relationship file's own reach-outs, behind the store's handle (`Store.part`)."""

    conn: sqlite3.Connection

    def add(self, r: Own) -> None:
        with write_tx(self.conn):
            self.conn.execute(
                "INSERT INTO own_reach_outs"
                " (id, relationship_id, kind, thing, draft, mode, detail, at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r.id,
                    r.relationship_id,
                    r.kind.value,
                    r.thing,
                    r.draft,
                    r.mode.value,
                    json.dumps(r.detail, sort_keys=True),
                    iso(r.at),
                ),
            )

    def since(self, rel: RelationshipId, start: datetime | None = None) -> list[Own]:
        rows = self.conn.execute(
            "SELECT * FROM own_reach_outs WHERE relationship_id = ? AND at >= ? ORDER BY at, id",
            (rel, iso(start) if start else ""),
        ).fetchall()
        out: list[Own] = []
        for r in rows:
            loaded: Json = json.loads(str(r["detail"]))
            out.append(
                Own(
                    str(r["id"]),
                    RelationshipId(str(r["relationship_id"])),
                    Kind(str(r["kind"])),
                    str(r["thing"]),
                    str(r["draft"]),
                    Mode(str(r["mode"])),
                    loaded if isinstance(loaded, dict) else {},
                    parse_iso(str(r["at"])),
                )
            )
        return out


def records(
    store: Store,
    rel: RelationshipId,
    start: datetime | None = None,
    kinds: Container[Kind] = tuple(Kind),
) -> list[ReachRecord]:
    """Every reach-out of the kinds asked for, from `start`, oldest first, whichever way it was
    stored: its own reasons' rows (dropped drafts included), the nudges it would have sent (their
    decisions) and the plans it would have reached out about (their rows)."""
    own = [
        ReachRecord(r.id, r.kind, r.mode, r.draft, r.at, r.thing, r.detail)
        for r in store.part(Reaches).since(rel, start)
    ]
    nudges = [
        ReachRecord(
            str(d.id),
            Kind.AWAY,
            Mode.SHADOW,
            str((d.detail or {}).get("draft") or ""),
            d.at,
            detail=d.detail or {},
        )
        for d in store.decisions_with_key(rel, WOULD_NUDGE, start)
    ]
    plans = [
        ReachRecord(
            r.id,
            Kind.PLAN,
            r.mode,
            r.draft,
            r.at,
            detail={"loop_id": r.loop_id, "reason": r.reason},
        )
        for r in store.reach_outs(rel, start)
    ]
    return sorted((r for r in [*own, *nudges, *plans] if r.kind in kinds), key=lambda r: r.at)
