"""`companion memory review`: the owner's questions about memory (ADR 0019), all of them until
[q]uit. Each answer is recorded; a retire goes through the logged retire path, and nothing is
deleted."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.consolidate import HELD, Label, Relation
from companion.core.merging import merged_kind
from companion.core.types import Belief, BeliefId, RelationshipId
from companion.loops.curate import merge, retire
from companion.store.sqlite.memory_checks import MemoryCheck
from companion.store.sqlite.merges import Proposal
from companion.store.sqlite.store import Store

ASKED = (Label.OUT_OF_DATE, Label.OVERSTATED, Label.PASSING)
CONFLICT = (Relation.REPLACES, Relation.CONTRADICTS)
WHY: dict[str, str] = {
    Label.OUT_OF_DATE: "looks out of date",
    Label.OVERSTATED: "states a habit from what reads like one occasion",
    Label.PASSING: "looks like a passing moment (sensitive, so it is your call)",
    Relation.REPLACES: "the later one may replace the earlier",
    Relation.CONTRADICTS: "these two may not both be true",
}


def _held(current: Mapping[BeliefId, Belief], bid: BeliefId) -> bool:
    return bid in current and current[bid].sensitivity >= HELD


def _pending(
    store: Store, rel: RelationshipId, current: Mapping[BeliefId, Belief]
) -> list[MemoryCheck | Proposal]:
    """Merges first, then the checks. A conflict between two memories that a pending merge would
    join is held back: pieces of one moment read as a contradiction when apart."""
    merges = [p for p in store.merge_proposals(rel) if p.answer is None]
    joined = [set(p.members) for p in merges]
    singles = [c for c in store.unanswered_checks(rel, list(ASKED)) if c.other_id is None]
    # a passing moment is asked about only when sensitive; the rest close on their own
    singles = [c for c in singles if c.verdict != Label.PASSING or _held(current, c.belief_id)]
    pairs = [
        c
        for c in store.unanswered_checks(rel, list(CONFLICT))
        if c.other_id is not None and not any({c.belief_id, c.other_id} <= j for j in joined)
    ]
    return [*merges, *sorted(singles + pairs, key=lambda c: c.id)]


def _merge_question(p: Proposal, current: Mapping[BeliefId, Belief]) -> str | None:
    if not all(m in current for m in p.members):
        return None
    lines = "\n".join(f"  - {current[m].claim}" for m in p.members)
    return (
        f"\nThese may be one memory:\n{lines}\n  as one: {p.claim}\n"
        "  [m]erge, keep [a]part, [s]kip, [q]uit: "
    )


def _merge_answer(  # noqa: PLR0913
    store: Store,
    rel: RelationshipId,
    p: Proposal,
    current: Mapping[BeliefId, Belief],
    *,
    choice: str,
    now: datetime,
) -> str | None:
    if choice == "a":
        store.answer_merge(p.id, "apart", now)
        return f"kept apart  {len(p.members)} memories"
    if choice != "m":
        return None
    kind = merged_kind([current[m] for m in p.members])
    done = merge(store, rel, list(p.members), p.claim, now, kind=kind, why="the owner agreed")
    store.answer_merge(p.id, "merged", now)
    return done


def _question(check: MemoryCheck, current: Mapping[BeliefId, Belief]) -> str | None:
    """The question for one check, or None when a memory it is about has since closed."""
    why = WHY[check.verdict]
    first = current.get(check.belief_id)
    if check.other_id is None:
        return (
            None
            if first is None
            else f"\n{first.claim}\n  {why}. [r]etire, [k]eep, [s]kip, [q]uit: "
        )
    second = current.get(check.other_id)
    if first is None or second is None:
        return None
    return (
        f"\n1. {first.claim}\n2. {second.claim}\n"
        f"  {why}. keep [1], keep [2], keep [b]oth, [s]kip, [q]uit: "
    )


def _answer(  # noqa: PLR0913
    store: Store,
    rel: RelationshipId,
    check: MemoryCheck,
    current: Mapping[BeliefId, Belief],
    *,
    choice: str,
    now: datetime,
) -> str | None:
    """Act on one answer and record it; None when it was skipped or not understood."""
    why = WHY[check.verdict]
    first = current[check.belief_id]
    if check.other_id is None:
        if choice == "r":
            retire(store, rel, first.id, f"{why}; the owner said retire", now)
            store.answer_check(check.id, "retire", now)
            return f"retired  {first.claim}"
        if choice == "k":
            store.answer_check(check.id, "keep", now)
            return f"kept     {first.claim}"
        return None
    second = current[check.other_id]
    if choice == "b":
        store.answer_check(check.id, "both", now)
        return f"kept both  {first.claim}\n           {second.claim}"
    if choice not in ("1", "2"):
        return None
    keep, drop = (first, second) if choice == "1" else (second, first)
    retire(store, rel, drop.id, f"{why}; the owner kept {keep.id[:8]}", now)
    store.answer_check(check.id, f"keep {choice}", now)
    return f"kept     {keep.claim}\nretired  {drop.claim}"


def review(
    db: Path,
    relationship: str,
    ask: Callable[[str], str] = input,
    per_sitting: int | None = None,
) -> str:
    store = Store(db)
    rel = RelationshipId(relationship)
    lines: list[str] = []
    try:
        pending = _pending(store, rel, {b.id: b for b in store.user_beliefs(rel)})
        if not pending:
            return "no questions about memory right now\n"
        answered = 0
        for item in pending[:per_sitting]:  # every question unless capped; [q]uit stops
            current = {b.id: b for b in store.user_beliefs(rel)}
            now = utc_now()
            is_merge = isinstance(item, Proposal)
            question = _merge_question(item, current) if is_merge else _question(item, current)
            if question is None:
                if isinstance(item, Proposal):
                    store.answer_merge(item.id, "gone", now)
                else:
                    store.answer_check(item.id, "gone", now)
                answered += 1
                continue
            choice = ask(question).strip().lower()[:1]
            if choice == "q":
                break
            line = (
                _merge_answer(store, rel, item, current, choice=choice, now=now)
                if isinstance(item, Proposal)
                else _answer(store, rel, item, current, choice=choice, now=now)
            )
            if line is not None:
                lines.append(line)
                answered += 1
        left = len(pending) - answered
        lines.append(f"{left} question{'s' if left != 1 else ''} left for another time")
    finally:
        store.close()
    return "\n".join(lines) + "\n"
