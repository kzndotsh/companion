"""`companion beliefs`: what it currently believes about you, with the quote behind each."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from companion.core.freshness import age_phrase, status
from companion.core.types import RelationshipId
from companion.core.views import is_settled
from companion.loops.curate import approve, close_duplicates, retire
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        rel = RelationshipId(relationship)
        found = store.user_beliefs(rel)
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


def opinions(db: Path, relationship: str) -> str:
    """The companion's own views: tentative until restated on a second day, then settled."""
    store = Store(db)
    try:
        rel = RelationshipId(relationship)
        found = store.self_beliefs(rel)
        days = store.evidence_days(rel)
        support = store.last_support(rel)
        approved = store.approved_views(rel)
    finally:
        store.close()
    if not found:
        return "no views recorded yet\n"
    now = datetime.now(UTC)
    lines: list[str] = []
    for b in sorted(found, key=lambda x: support.get(x.id, x.valid_from), reverse=True):
        n = days.get(b.id, 1)
        state = "settled" if is_settled(b, days) else "tentative"
        mark = "APPROVED" if b.id in approved else "not approved"
        age = age_phrase(now - support.get(b.id, b.valid_from))
        lines.append(f"{b.id[:8]} [{b.kind}] {mark}, {state} ({n} day(s), last {age})  {b.claim}")
        lines.append(f'    "{b.evidence[0].quote}"')
    settled = sum(is_settled(b, days) for b in found)
    live = sum(b.id in approved for b in found)
    return (
        "\n".join(lines)
        + f"\n\n{len(found)} views, {settled} settled, {live} approved"
        + " (only approved views reach the card)\n"
        + "approve: companion approve <id>    remove: companion retire <id> --reason ...\n"
    )


def approve_one(db: Path, relationship: str, id_prefix: str) -> str:
    store = Store(db)
    try:
        return approve(store, RelationshipId(relationship), id_prefix) + "\n"
    finally:
        store.close()
