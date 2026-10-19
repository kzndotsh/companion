"""`companion beliefs`: what it currently believes about you, with the quote behind each."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from companion.core.freshness import status, when_phrase
from companion.core.types import RelationshipId
from companion.core.views import ViewMode, gates, is_settled, parse_mode
from companion.loops.calibrate import report, reviewed_views
from companion.loops.curate import approve, close_duplicates, merge, retire
from companion.store.sqlite.store import VIEWS_MODE_KEY, Store


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
        fresh = f"{status(b.kind, last, now)} {when_phrase(last, now)}, {len(b.evidence)} quote(s)"
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


def merge_some(db: Path, relationship: str, id_prefixes: list[str], claim: str) -> str:
    store = Store(db)
    try:
        return merge(store, RelationshipId(relationship), id_prefixes, claim) + "\n"
    finally:
        store.close()


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
        checks = store.view_checks(rel)
        mode = parse_mode(store.setting(rel, VIEWS_MODE_KEY))
    finally:
        store.close()
    if not found:
        return "no views recorded yet\n"
    now = datetime.now(UTC)
    lines: list[str] = []
    for b in sorted(found, key=lambda x: support.get(x.id, x.valid_from), reverse=True):
        n = days.get(b.id, 1)
        state = "settled" if is_settled(b, days) else "tentative"
        g = gates(b, days, checks)
        mark = (
            "APPROVED"
            if b.id in approved
            else ("auto-eligible" if g.eligible and mode is ViewMode.AUTO else "not in the card")
        )
        age = when_phrase(support.get(b.id, b.valid_from), now)
        lines.append(f"{b.id[:8]} [{b.kind}] {mark}, {state} ({n} day(s), last {age})  {b.claim}")
        lines.append(f'    "{b.evidence[0].quote}"')
    settled = sum(is_settled(b, days) for b in found)
    live = sum(b.id in approved for b in found)
    return (
        "\n".join(lines)
        + f"\n\nmode: {mode}. {len(found)} views, {settled} settled, {live} approved\n"
        + "approve: companion approve <id>    remove: companion retire <id> --reason ...\n"
    )


def approve_one(db: Path, relationship: str, id_prefix: str) -> str:
    store = Store(db)
    try:
        return approve(store, RelationshipId(relationship), id_prefix) + "\n"
    finally:
        store.close()


def views_mode(db: Path, relationship: str, mode: str | None) -> str:
    """Show or set how views reach the card: auto, review (approved only) or off."""
    from datetime import UTC, datetime  # noqa: PLC0415

    store = Store(db)
    try:
        rel = RelationshipId(relationship)
        if mode is None:
            return f"views mode: {parse_mode(store.setting(rel, VIEWS_MODE_KEY))}\n"
        chosen = ViewMode(mode)
        store.set_setting(rel, VIEWS_MODE_KEY, chosen.value, datetime.now(UTC))
        return f"views mode set to {chosen}\n"
    finally:
        store.close()


def calibrate(db: Path, relationship: str) -> str:
    store = Store(db)
    try:
        return report(reviewed_views(store, RelationshipId(relationship)))
    finally:
        store.close()
