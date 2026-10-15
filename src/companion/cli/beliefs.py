"""`companion beliefs`: what it currently believes about you, with the quote behind each."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from companion.core.freshness import age_phrase, status
from companion.core.types import RelationshipId
from companion.loops.curate import close_duplicates, retire
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        rel = RelationshipId(relationship)
        found = store.current_beliefs(rel)
        support = store.last_support(rel)
    finally:
        store.close()
    if not found:
        return "no beliefs yet\n"
    now = datetime.now(UTC)
    lines: list[str] = []
    for b in sorted(found, key=lambda x: (x.kind, x.valid_from)):
        quote = b.evidence[0].quote
        last = support.get(b.id, b.valid_from)
        fresh = f"{status(b.kind, last, now)} {age_phrase(now - last)}, {len(b.evidence)} quote(s)"
        lines.append(
            f"{b.id[:8]} [{b.kind}/{b.provenance}] {fresh}  sens {b.sensitivity}"
            f"  {b.claim}"
            f'\n    "{quote}"'
        )
    return "\n".join(lines) + f"\n\n{len(found)} current beliefs\n"


def dedupe(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        report = close_duplicates(store, RelationshipId(relationship))
    finally:
        store.close()
    return ("\n".join(report) + "\n") if report else "no duplicates\n"


def retire_one(db: Path, relationship: str, id_prefix: str, reason: str) -> str:
    store = Store(db)
    try:
        return retire(store, RelationshipId(relationship), id_prefix, reason) + "\n"
    finally:
        store.close()
