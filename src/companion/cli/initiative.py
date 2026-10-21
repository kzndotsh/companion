"""`companion initiative`: the open loops, what shadow mode would have sent, and the nudges after
they stepped away (times away it read, and the nudges it would have sent)."""

from __future__ import annotations

from pathlib import Path

from companion.core.nudges import AWAY, WOULD_NUDGE
from companion.core.types import DecisionKind, RelationshipId
from companion.loops.openloops import HELD
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        loops = store.open_loops(rel)
        reach = store.reach_outs(rel)
        held = store.decisions_of_kind(rel, DecisionKind.DO_NOTHING)
        held = [d for d in held if d.has_key(HELD)]
        away = [d for d in store.decisions_of_kind(rel, DecisionKind.POLICY) if d.has_key(AWAY)]
        nudges = [
            d for d in store.decisions_of_kind(rel, DecisionKind.INITIATE) if d.has_key(WOULD_NUDGE)
        ]
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
    return "\n".join(out) + "\n"
