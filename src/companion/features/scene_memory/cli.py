"""`companion scene`: the intimate scene lane (ADR 0026) by stance, with quotes and how much
evidence each has; the patterns waiting for a second scene; the memories kept out of scenes with
the reason, where one kept out by the floor shows only its id; and the retired patterns.
`companion retire ID` retires a pattern, or a memory as any other."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from companion.core.clock import utc_now
from companion.core.frames import is_assertable
from companion.core.types import Belief, BeliefId, RelationshipId, UtteranceId
from companion.features.scene_memory.logic import (
    WHY_TEXT,
    Everyday,
    Excluded,
    Intimate,
    Pattern,
    Place,
    Stance,
    Why,
    pattern_entry,
    screen,
    touches_age,
)
from companion.features.scene_memory.run import facts_of
from companion.store.sqlite.store import Store

type Marks = tuple[frozenset[UtteranceId], frozenset[UtteranceId]]  # held, heavy
WAITING = "patterns seen in one scene so far"
KEPT_OUT = "kept out of scenes"
RETIRED = "retired patterns"
_TITLES = {
    Stance.HARD_LIMIT: "hard limits",
    Stance.SOFT_LIMIT: "soft limits",
    Stance.INTO: "into",
    Stance.CURIOUS: "curious",
    Stance.STYLE: "style",
    Stance.AFTERCARE: "aftercare",
}


def _quotes(quotes: tuple[str, ...]) -> list[str]:
    return [f'    "{q}"' for q in quotes]


def _belief(b: Belief) -> list[str]:
    return [
        f"{b.id[:8]}  {b.claim}  ({len(b.evidence)} quote(s))",
        *_quotes(tuple(e.quote for e in b.evidence)),
    ]


def _pattern(p: Pattern) -> list[str]:
    return [
        f"{p.id[:8]}  {p.claim}  ({p.scenes} scene(s))",
        *_quotes(tuple(q.text for q in p.quotes)),
    ]


type Sections = dict[str, list[str]]


def _place_beliefs(
    beliefs: list[Belief], places: Mapping[BeliefId, Place], facts: Marks, out: Sections
) -> None:
    held, heavy = facts
    for b in beliefs:
        match screen(places[b.id], b, facts_of(b, held, heavy)):
            case Intimate(stance):
                out[_TITLES[stance]] += _belief(b)
            case Excluded(Why.FLOOR):
                out[KEPT_OUT].append(f"{b.id[:8]}  {WHY_TEXT[Why.FLOOR]}")
            case Excluded(why):
                out[KEPT_OUT].append(f"{b.id[:8]}  {b.claim}  ({WHY_TEXT[why]})")
            case Everyday():
                pass


def _place_patterns(patterns: list[Pattern], held: frozenset[UtteranceId], out: Sections) -> None:
    for p in patterns:
        floor = touches_age(p.claim) or any(q.utterance in held for q in p.quotes)
        if p.retired:
            out[RETIRED].append(f"{p.id[:8]}  retired" if floor else f"{p.id[:8]}  {p.claim}")
        elif floor:
            out[KEPT_OUT].append(f"{p.id[:8]}  {WHY_TEXT[Why.FLOOR]}")
        elif pattern_entry(p, held) is not None:
            out[_TITLES[p.stance]] += _pattern(p)
        else:
            out[WAITING] += _pattern(p)


def run(db: Path, relationship: str) -> str:
    rel = RelationshipId(relationship)
    store = Store(db)
    try:
        sm = store.scene_memory()
        places = sm.places(rel)
        beliefs = [b for b in store.user_beliefs(rel) if is_assertable(b) and b.id in places]
        patterns = sm.patterns(rel)
        facts = sm.facts(
            rel,
            [
                *(e.utterance_id for b in beliefs for e in b.evidence),
                *(q.utterance for p in patterns for q in p.quotes),
            ],
        )
    finally:
        store.close()
    out: Sections = {t: [] for t in (*_TITLES.values(), WAITING, KEPT_OUT, RETIRED)}
    _place_beliefs(beliefs, places, facts, out)
    _place_patterns(patterns, facts[0], out)
    lines = [line for title, rows in out.items() if rows for line in (f"{title}:", *rows, "")]
    return "\n".join(lines) if lines else "nothing in the scene lane yet\n"


def retire_pattern(store: Store, rel: RelationshipId, id_prefix: str, reason: str) -> str | None:
    """Retire the one pattern whose id starts with the prefix. None when none matches, so the
    caller can say so."""
    matches = [
        p
        for p in store.scene_memory().patterns(rel)
        if p.id.startswith(id_prefix) and not p.retired
    ]
    if not matches:
        return None
    if len(matches) > 1:
        msg = f"{len(matches)} patterns start with {id_prefix!r}; need exactly one"
        raise ValueError(msg)
    store.scene_memory().retire(matches[0].id, reason, utc_now())
    return f"retired  {matches[0].id[:8]}"
