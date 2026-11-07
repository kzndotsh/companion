"""`companion memory review`: the owner's questions about memory (ADR 0019), all of them until
[q]uit. Each answer is recorded; a retire goes through the logged retire path, and nothing is
deleted."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.sensitivity import GUARDED_AT
from companion.core.types import Belief, BeliefId, RelationshipId
from companion.features.upkeep.merging.logic import (
    Noted,
    Picked,
    Settled,
    decode,
    encode,
    merged_kind,
)
from companion.features.upkeep.merging.store import MergeProposals, Proposal
from companion.features.upkeep.reread import logic as reread
from companion.features.upkeep.reread.logic import CONFLICT, Label, Said
from companion.features.upkeep.reread.store import MemoryCheck, MemoryChecks
from companion.features.upkeep.sort import logic as sort
from companion.kit.curate import merge, retire
from companion.store.sqlite.store import Store

ASKED = (*reread.ASKED, *sort.ASKED)
WHY = {**reread.WHY, **sort.WHY}


def _held(current: Mapping[BeliefId, Belief], bid: BeliefId) -> bool:
    return bid in current and current[bid].sensitivity >= GUARDED_AT


def _open(p: Proposal) -> bool:
    """Unanswered, or answered only with a note: a note keeps it for another time."""
    return p.answer is None or isinstance(decode(p.answer), Noted)


def _pending(
    store: Store, rel: RelationshipId, current: Mapping[BeliefId, Belief]
) -> list[MemoryCheck | Proposal]:
    """Merges first, then the checks. A conflict between two memories that a pending merge would
    join is held back: pieces of one moment read as a contradiction when apart."""
    merges = [p for p in store.part(MergeProposals).all_(rel) if _open(p)]
    joined = [set(p.members) for p in merges]
    singles = [c for c in store.part(MemoryChecks).unanswered(rel, ASKED) if c.other_id is None]
    # a passing moment is asked about only when sensitive; the rest close on their own
    singles = [c for c in singles if c.verdict != Label.PASSING or _held(current, c.belief_id)]
    pairs = [
        c
        for c in store.part(MemoryChecks).unanswered(rel, list(CONFLICT))
        if c.other_id is not None and not any({c.belief_id, c.other_id} <= j for j in joined)
    ]
    return [*merges, *sorted(singles + pairs, key=lambda c: c.id)]


def _merge_question(p: Proposal, current: Mapping[BeliefId, Belief]) -> str | None:
    if not all(m in current for m in p.members):
        return None
    lines = "\n".join(f"  {i}. {current[m].claim}" for i, m in enumerate(p.members, start=1))
    note = decode(p.answer)
    noted = f"\n  your note: {note.why}" if isinstance(note, Noted) else ""
    return (
        f"\nThese may be one memory:\n{lines}\n  as one: {p.claim}{noted}\n"
        "  [m]erge, [p]ick which belong, [w]ord it yourself, keep [a]part, [n]ote why, [s]kip,"
        " [q]uit: "
    )


def picked(said: str, size: int) -> list[int] | None:
    """The members they named ("1 2 4"), as positions, when two or more are valid."""
    nums = sorted({int(x) - 1 for x in said.replace(",", " ").split() if x.isdigit()})
    valid = [n for n in nums if 0 <= n < size]
    return valid if len(valid) >= 2 and len(valid) == len(nums) else None


def _merge_answer(  # noqa: PLR0911, PLR0913
    store: Store,
    rel: RelationshipId,
    p: Proposal,
    current: Mapping[BeliefId, Belief],
    *,
    choice: str,
    ask: Callable[[str], str],
    now: datetime,
) -> str | None:
    """Act on one answer to a merge question; None when it was skipped or not understood."""
    members = [current[m] for m in p.members]
    if choice == "a":
        store.part(MergeProposals).answer(p.id, encode(Settled.APART), now)
        return f"kept apart  {len(members)} memories"
    if choice == "n":
        why = " ".join(ask("  why? ").split())
        if not why:
            return None
        store.part(MergeProposals).answer(p.id, encode(Noted(why)), now)
        return f"noted      {why}"
    if choice == "p":
        which = picked(ask("  which belong together (for example 1 2 4)? "), len(members))
        if which is None:
            return None
        store.part(MergeProposals).answer(p.id, encode(Picked(tuple(n + 1 for n in which))), now)
        return "picked     a new wording for those is proposed at the next grouping"
    if choice == "w":
        claim = " ".join(ask("  your wording: ").split())
        if not claim:
            return None
        done = merge(
            store,
            rel,
            list(p.members),
            claim,
            now,
            kind=merged_kind(members),
            why="worded by the owner",
        )
        store.part(MergeProposals).answer(p.id, encode(Settled.WORDED), now)
        return done
    if choice != "m":
        return None
    done = merge(
        store, rel, list(p.members), p.claim, now, kind=merged_kind(members), why="the owner agreed"
    )
    store.part(MergeProposals).answer(p.id, encode(Settled.MERGED), now)
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
            store.part(MemoryChecks).answer(check.id, Said.RETIRE, now)
            return f"retired  {first.claim}"
        if choice == "k":
            store.part(MemoryChecks).answer(check.id, Said.KEEP, now)
            return f"kept     {first.claim}"
        return None
    second = current[check.other_id]
    if choice == "b":
        store.part(MemoryChecks).answer(check.id, Said.BOTH, now)
        return f"kept both  {first.claim}\n           {second.claim}"
    if choice not in ("1", "2"):
        return None
    keep, drop = (first, second) if choice == "1" else (second, first)
    retire(store, rel, drop.id, f"{why}; the owner kept {keep.id[:8]}", now)
    store.part(MemoryChecks).answer(
        check.id, Said.KEEP_FIRST if choice == "1" else Said.KEEP_SECOND, now
    )
    return f"kept     {keep.claim}\nretired  {drop.claim}"


def review(
    db: Path,
    relationship: str,
    ask: Callable[[str], str] = input,
    per_sitting: int | None = None,
) -> str:
    rel = RelationshipId(relationship)
    lines: list[str] = []
    with Store(db) as store:
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
                    store.part(MergeProposals).answer(item.id, encode(Settled.GONE), now)
                else:
                    store.part(MemoryChecks).answer(item.id, Said.GONE, now)
                answered += 1
                continue
            choice = ask(question).strip().lower()[:1]
            if choice == "q":
                break
            line = (
                _merge_answer(store, rel, item, current, choice=choice, ask=ask, now=now)
                if isinstance(item, Proposal)
                else _answer(store, rel, item, current, choice=choice, now=now)
            )
            if line is not None:
                lines.append(line)
                answered += 1
        left = len(pending) - answered
        lines.append(f"{left} question{'s' if left != 1 else ''} left for another time")
    return "\n".join(lines) + "\n"
