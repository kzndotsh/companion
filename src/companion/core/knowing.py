"""A map of what it knows about them, and the gap it would ask about (J48).

It asked plenty of questions, but only about the thing just said, so memory filled up with food and
music and held almost nothing about their hopes or values. Each memory gets a label for the part of
their life it is about and how personal it is. A model labels; code keeps the counts and picks the
thinnest part of the map that is fine to ask about. For now the pick is only logged (shadow).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from companion.core.types import Belief, BeliefId, Json
from companion.prompts import get


class Domain(StrEnum):
    IDENTITY = "identity"  # who they are and what to call them
    PEOPLE = "people"  # family, friends, partners, pets
    DAILY = "daily"  # daily life, work, home, routines
    INTERESTS = "interests"  # tastes, hobbies, media, food
    HISTORY = "history"  # their past and the stories that formed them
    HOPES = "hopes"  # plans, goals, what they want
    VALUES = "values"  # what they believe and care about
    INNER = "inner"  # feelings, health, struggles, desires


class Depth(StrEnum):
    SURFACE = "surface"
    PERSONAL = "personal"
    CORE = "core"


# Their inner life is only ever received, never asked about.
ASKABLE = (
    Domain.IDENTITY,
    Domain.PEOPLE,
    Domain.DAILY,
    Domain.INTERESTS,
    Domain.HISTORY,
    Domain.HOPES,
    Domain.VALUES,
)


@dataclass(frozen=True, slots=True)
class Label:
    belief_id: BeliefId
    domain: Domain
    depth: Depth


@dataclass(frozen=True, slots=True)
class Gap:
    domain: Domain
    depth: Depth
    counts: Mapping[Domain, int]

    @property
    def reason(self) -> str:
        counts = ", ".join(f"{d.value} {self.counts.get(d, 0)}" for d in Domain)
        return (
            f"map: the thinnest part to ask about is {self.domain.value}"
            f" ({self.counts.get(self.domain, 0)} memories; {counts})"
        )


WOULD_ASK = "map: would ask about a gap (shadow)"
MAP_EVERY = timedelta(hours=24)
LABEL_PROMPT = get("system/memory-map")
LABEL_BATCH = 60
LABEL_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string"},
                    "domain": {"type": "string", "enum": [d.value for d in Domain]},
                    "depth": {"type": "string", "enum": [d.value for d in Depth]},
                },
                "required": ["ref", "domain", "depth"],
            },
        }
    },
    "required": ["labels"],
}


def label_prompt(beliefs: Iterable[Belief]) -> tuple[str, dict[str, BeliefId]]:
    """The memories to label, each under a short ref, and the refs back to their ids."""
    refs = {f"r{n}": b.id for n, b in enumerate(beliefs, 1)}
    claims = {b.id: b.claim for b in beliefs}
    return "\n".join(f"[{ref}] {claims[bid]}" for ref, bid in refs.items()), refs


def parse_labels(data: Json, refs: Mapping[str, BeliefId]) -> list[Label]:
    """The labels the model gave, keeping only known refs and known values, one per memory."""
    items = data.get("labels") if isinstance(data, dict) else None
    out: dict[BeliefId, Label] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        ref, domain, depth = item.get("ref"), item.get("domain"), item.get("depth")
        if not isinstance(ref, str) or ref not in refs or refs[ref] in out:
            continue
        if domain not in set(Domain) or depth not in set(Depth):
            continue
        out[refs[ref]] = Label(refs[ref], Domain(str(domain)), Depth(str(depth)))
    return list(out.values())


def counts(beliefs: Iterable[Belief], labels: Mapping[BeliefId, Label]) -> Counter[Domain]:
    return Counter(labels[b.id].domain for b in beliefs if b.id in labels)


def pick_gap(beliefs: Iterable[Belief], labels: Mapping[BeliefId, Label]) -> Gap | None:
    """The thinnest askable part of the map, first in `ASKABLE` order on a tie. Only the surface is
    asked about until closeness can set the depth (T17). None when nothing is labelled yet."""
    have = counts(beliefs, labels)
    if not have:
        return None
    domain = min(ASKABLE, key=lambda d: have.get(d, 0))
    return Gap(domain, Depth.SURFACE, dict(have))


__all__ = [
    "ASKABLE",
    "LABEL_BATCH",
    "LABEL_PROMPT",
    "LABEL_SCHEMA",
    "MAP_EVERY",
    "WOULD_ASK",
    "Depth",
    "Domain",
    "Gap",
    "Label",
    "counts",
    "label_prompt",
    "parse_labels",
    "pick_gap",
]
