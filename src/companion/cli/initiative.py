"""`companion initiative`: the open loops, what shadow mode would have sent, the nudges after
they stepped away (times away it read, and the nudges it would have sent), and its reach-outs for
its own reasons (ADR 0021): their learned rhythm, its share against the dial, its would-sends and
its holds."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from companion.core.clock import local_zone, utc_now
from companion.core.reachout import HELD_KEYS, WOULD_NUDGE, dial
from companion.core.switch import REACH
from companion.core.turn.now import KEY as NOW_KEY
from companion.core.turn.now import Phase, from_decisions
from companion.core.types import RelationshipId
from companion.features.reach import cli as own_reasons
from companion.features.reach.run import resume as resume_reach
from companion.features.threads.store import Threads
from companion.kit.command import Command, Group, db_args, emit, target
from companion.settings import Settings
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str, now: datetime | None = None) -> str:
    """`now` pins the time for a test; the wall clock otherwise."""
    rel = RelationshipId(relationship)
    with Store(db) as store:
        loops = store.part(Threads).loops(rel)
        reach = store.reach_outs(rel)
        held = sorted(
            (d for key in HELD_KEYS for d in store.decisions_with_key(rel, key)),
            key=lambda d: d.at,
        )
        said = from_decisions(store.decisions_with_key(rel, NOW_KEY))
        away = [s for s in said if s.label.phase is Phase.LEAVING]
        nudges = store.decisions_with_key(rel, WOULD_NUDGE)
        own = own_reasons.lines(
            store,
            rel,
            (now or utc_now(), local_zone()),
            dial(Settings.from_env().position(REACH)),
        )
    out = ["open loops (state, kind, when to reach out, what they said)"]
    out += [
        f"  {lp.state:8} {lp.kind:9} {lp.follow_up_at:%a %m-%d %H:%M}  {lp.claim}"
        f'  "{lp.quote[:60]}"'
        for lp in loops
    ] or ["  none yet"]
    out += ["", "shadow reach-outs (would have sent)"]
    out += [f"  {r.at:%m-%d %H:%M}  {r.draft or '(no draft)'}  [{r.reason}]" for r in reach] or [
        "  none yet"
    ]
    out += ["", "held (due, but something was in the way: a plan or its own reasons)"]
    out += [f"  {d.at:%m-%d %H:%M}  {d.reason}" for d in held] or ["  none"]
    out += ["", f"stepped away ({len(away)} read), and the nudges it would have sent (shadow)"]
    out += [
        f"  {d.at:%m-%d %H:%M}  {(d.detail or {}).get('draft') or '(no draft)'}"
        f"  [after {(d.detail or {}).get('said', '')!r:.60}]"
        for d in nudges
    ] or ["  none yet"]
    out += ["", *own]
    return "\n".join(out) + "\n"


def resume(db: Path, relationship: str, now: datetime | None = None) -> str:
    """Turn reaching out back on after they asked it to stop (issue 123)."""
    with Store(db) as store:
        done = resume_reach(store, RelationshipId(relationship), now or utc_now())
    if not done:
        return "reaching out is not stopped; nothing to resume\n"
    return "reaching out is back on: they asked it to stop, and you turned it back on\n"


def _args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--resume",
        action="store_true",
        help="turn reaching out back on after they asked it to stop",
    )
    db_args(p)


def _run(a: argparse.Namespace) -> int:
    if a.resume:
        return emit(resume(*target(a)))
    return emit(run(*target(a)))


COMMANDS = (
    Command(
        "initiative",
        Group.REACH,
        "open loops, and the messages it would send you first",
        _run,
        _args,
    ),
)
