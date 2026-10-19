"""`companion memory review`: the owner's questions about memory (ADR 0019), a few at a time. Each
answer is recorded; a retire goes through the logged retire path, and nothing is deleted."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.consolidate import HELD, Label
from companion.core.types import Belief, BeliefId, RelationshipId
from companion.loops.curate import retire
from companion.store.sqlite.store import Store

PER_SITTING = 5
ASKED = (Label.OUT_OF_DATE, Label.OVERSTATED, Label.PASSING)
WHY = {
    Label.OUT_OF_DATE: "looks out of date",
    Label.OVERSTATED: "states a habit from what reads like one occasion",
    Label.PASSING: "looks like a passing moment (sensitive, so it is your call)",
}


def _held(current: Mapping[BeliefId, Belief], bid: BeliefId) -> bool:
    return bid in current and current[bid].sensitivity >= HELD


def review(
    db: Path, relationship: str, ask: Callable[[str], str] = input, per_sitting: int = PER_SITTING
) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    lines: list[str] = []
    try:
        current = {b.id: b for b in store.user_beliefs(rel)}
        pending = [c for c in store.unanswered_checks(rel, list(ASKED)) if c.other_id is None]
        # a passing moment is asked about only when sensitive; the rest close on their own
        pending = [c for c in pending if c.verdict != Label.PASSING or _held(current, c.belief_id)]
        if not pending:
            return "no questions about memory right now\n"
        for check in pending[:per_sitting]:
            b = current.get(check.belief_id)
            now = utc_now()
            if b is None:
                store.answer_check(check.id, "gone", now)
                continue
            why = WHY[Label(check.verdict)]
            said = ask(f"\n{b.claim}\n  {why}. [r]etire, [k]eep, [s]kip, [q]uit: ")
            choice = said.strip().lower()[:1]
            if choice == "q":
                break
            if choice == "r":
                retire(store, rel, b.id, f"{why}; the owner said retire", now)
                store.answer_check(check.id, "retire", now)
                lines.append(f"retired  {b.claim}")
            elif choice == "k":
                store.answer_check(check.id, "keep", now)
                lines.append(f"kept     {b.claim}")
        left = len(pending) - len(lines)
        lines.append(f"{left} question{'s' if left != 1 else ''} left for another time")
    finally:
        store.close()
    return "\n".join(lines) + "\n"
