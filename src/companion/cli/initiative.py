"""`companion initiative`: the open loops, what shadow mode would have sent, the nudges after
they stepped away (times away it read, and the nudges it would have sent), and its reach-outs for
its own reasons (ADR 0021): their learned rhythm, its share against the dial, its would-sends and
its holds."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from companion.core.clock import local_zone, utc_now
from companion.core.reachout import WOULD_NUDGE
from companion.core.types import RelationshipId
from companion.features.nudges.logic import AWAY
from companion.features.reach import cli as own_reasons
from companion.features.reach.logic import dial
from companion.features.threads.run import HELD
from companion.settings import Settings
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str, now: datetime | None = None) -> str:
    """`now` pins the time for a test; the wall clock otherwise."""
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        loops = store.open_loops(rel)
        reach = store.reach_outs(rel)
        held = store.decisions_with_key(rel, HELD)
        away = store.decisions_with_key(rel, AWAY)
        nudges = store.decisions_with_key(rel, WOULD_NUDGE)
        own = own_reasons.lines(
            store, rel, (now or utc_now(), local_zone()), dial(Settings.from_env().mode("reach"))
        )
    finally:
        store.close()
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
    out += ["", "held (due, but something was in the way)"]
    out += [f"  {d.at:%m-%d %H:%M}  {d.reason}" for d in held] or ["  none"]
    out += ["", f"stepped away ({len(away)} read), and the nudges it would have sent (shadow)"]
    out += [
        f"  {d.at:%m-%d %H:%M}  {(d.detail or {}).get('draft') or '(no draft)'}"
        f"  [after {(d.detail or {}).get('said', '')!r:.60}]"
        for d in nudges
    ] or ["  none yet"]
    out += ["", *own]
    return "\n".join(out) + "\n"
