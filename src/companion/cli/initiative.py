"""`companion initiative`: the open loops and what shadow mode would have sent."""

from __future__ import annotations

from pathlib import Path

from companion.core.types import DecisionKind, RelationshipId
from companion.store.sqlite.store import Store


def run(db: Path, relationship: str) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    try:
        loops = store.open_loops(rel)
        reach = store.reach_outs(rel)
        held = store.decisions_of_kind(rel, DecisionKind.DO_NOTHING)
        held = [d for d in held if d.reason.startswith("held, would otherwise")]
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
    return "\n".join(out) + "\n"
