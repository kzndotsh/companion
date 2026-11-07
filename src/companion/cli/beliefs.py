"""`companion beliefs`: what it currently believes about you, with the quote behind each."""

from __future__ import annotations

import argparse
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.freshness import status, when_phrase
from companion.core.types import RelationshipId
from companion.core.views import ViewMode, gates, is_settled, overstated, parse_mode
from companion.features.history.cli import retire_story
from companion.features.intimate.cli import retire_pattern
from companion.kit.command import Command, Group, db_args, emit, plain, target
from companion.kit.curate import approve, close_duplicates, merge, retire
from companion.memory.calibrate import report, reviewed_views
from companion.store.sqlite.store import VIEWS_MODE_KEY, Store


def run(db: Path, relationship: str) -> str:
    with Store(db) as store:
        rel = RelationshipId(relationship)
        found = store.user_beliefs(rel)
        support = store.last_support(rel)
    if not found:
        return "no beliefs yet\n"
    now = utc_now()
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
    with Store(db) as store:
        report = close_duplicates(store, RelationshipId(relationship))
    return ("\n".join(report) + "\n") if report else "no duplicates\n"


def merge_some(db: Path, relationship: str, id_prefixes: list[str], claim: str) -> str:
    with Store(db) as store:
        return merge(store, RelationshipId(relationship), id_prefixes, claim) + "\n"


def retire_one(db: Path, relationship: str, id_prefix: str, reason: str) -> str:
    """Retire a belief or view by id prefix, or, when no current belief has that prefix, a story of
    its own past (ADR 0025) or a pattern from scenes (ADR 0026)."""
    rel = RelationshipId(relationship)
    with Store(db) as store:
        if not any(b.id.startswith(id_prefix) for b in store.current_beliefs(rel)):
            done = retire_story(store, rel, id_prefix, reason) or retire_pattern(
                store, rel, id_prefix, reason
            )
            if done is not None:
                return done + "\n"
        return retire(store, rel, id_prefix, reason) + "\n"


def opinions(db: Path, relationship: str) -> str:
    """The companion's own views: tentative until restated on a second day, then settled."""
    with Store(db) as store:
        rel = RelationshipId(relationship)
        found = store.self_beliefs(rel)
        days = store.evidence_days(rel)
        support = store.last_support(rel)
        approved = store.approved_views(rel)
        checks = store.view_checks(rel)
        mode = parse_mode(store.setting(rel, VIEWS_MODE_KEY))
    if not found:
        return "no views recorded yet\n"
    now = utc_now()
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
        hedge = overstated(b)
        if hedge is not None:
            mark += f", OVERSTATED (it said {hedge!r})"
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
    with Store(db) as store:
        return approve(store, RelationshipId(relationship), id_prefix) + "\n"


def views_mode(db: Path, relationship: str, mode: str | None) -> str:
    """Show or set how views reach the card: auto, review (approved only) or off."""
    with Store(db) as store:
        rel = RelationshipId(relationship)
        if mode is None:
            return f"views mode: {parse_mode(store.setting(rel, VIEWS_MODE_KEY))}\n"
        chosen = ViewMode(mode)
        store.set_setting(rel, VIEWS_MODE_KEY, chosen.value, utc_now())
        return f"views mode set to {chosen}\n"


def calibrate(db: Path, relationship: str) -> str:
    with Store(db) as store:
        return report(reviewed_views(store, RelationshipId(relationship)))


def _merge_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("id_prefix", nargs="+")
    p.add_argument("--claim", required=True, help="the merged wording")
    db_args(p)


def _retire_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("id_prefix")
    p.add_argument("--reason", required=True)
    db_args(p)


def _approve_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("id_prefix")
    db_args(p)


def _views_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--mode", choices=[m.value for m in ViewMode])
    db_args(p)


COMMANDS = (
    plain("beliefs", Group.MEMORY, "what it currently believes, with quotes", run),
    Command(
        "merge",
        Group.MEMORY,
        "merge beliefs that say one thing into one, keeping every quote",
        lambda a: emit(merge_some(*target(a), [str(x) for x in a.id_prefix], str(a.claim))),
        _merge_args,
    ),
    Command(
        "retire",
        Group.MEMORY,
        "close one belief, or retire a story of its past, by id prefix",
        lambda a: emit(retire_one(*target(a), str(a.id_prefix), str(a.reason))),
        _retire_args,
    ),
    plain("dedupe", Group.MEMORY, "close beliefs that rest on the same words", dedupe),
    plain("opinions", Group.ITSELF, "the companion's own views, tentative or settled", opinions),
    Command(
        "approve",
        Group.ITSELF,
        "approve one of the companion's own views, so it reaches the card",
        lambda a: emit(approve_one(*target(a), str(a.id_prefix))),
        _approve_args,
    ),
    Command(
        "views",
        Group.ITSELF,
        "show or set how the companion's views reach the card",
        lambda a: emit(views_mode(*target(a), a.mode)),
        _views_args,
    ),
    plain(
        "calibrate", Group.MEASURING, "compare the automatic gates with your approvals", calibrate
    ),
)
