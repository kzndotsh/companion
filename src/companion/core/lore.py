"""Which of the companion's views are its lore (ADR 0020, phase 1).

The views ledger records what it says about itself, but mixes its own tastes with advice it gave,
rules for how it treats the user, facts about what it is, and the odd claim of a lived event. A
small model labels each view with one kind; code reads only `taste` as lore and never counts
`lived` (A22). Shadow: nothing reaches the talker yet.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from companion.core.types import Belief, BeliefId, Json
from companion.prompts import get

PROMPT = get("system/lore-label")
_NOTE = get("notes/lore")
SHOWN = 2  # at most this many of its tastes a turn
GATE = 0.3  # a taste less like their message than this is not shown
BATCH = 60


class Kind(StrEnum):
    TASTE = "taste"
    STANCE = "stance"
    RULE = "rule"
    SELF = "self"
    LIVED = "lived"


SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string"},
                    "kind": {"type": "string", "enum": [k.value for k in Kind]},
                },
                "required": ["ref", "kind"],
            },
        }
    },
    "required": ["labels"],
}


@dataclass(frozen=True, slots=True)
class Labelled:
    belief_id: BeliefId
    kind: Kind


def prompt(views: Iterable[Belief]) -> tuple[str, dict[str, BeliefId]]:
    """Each view under a short ref with the words it said, and the refs back to their ids."""
    listed = list(views)
    refs = {f"v{n}": b.id for n, b in enumerate(listed, 1)}
    lines = [
        f'[{ref}] {b.claim} (it said: "{b.evidence[0].quote}")'
        for ref, b in zip(refs, listed, strict=True)
    ]
    return "\n".join(lines), refs


def parse(data: Json, refs: Mapping[str, BeliefId]) -> list[Labelled] | None:
    """One label per view it was shown, known kinds only. None for an answer of the wrong shape."""
    items = data.get("labels") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    out: dict[BeliefId, Labelled] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        bid = refs.get(str(item.get("ref", "")).strip("[] "))
        kind = item.get("kind")
        if bid is None or bid in out or kind not in set(Kind):
            continue
        out[bid] = Labelled(bid, Kind(str(kind)))
    return list(out.values())


def lore(views: Iterable[Belief], labels: Mapping[BeliefId, Kind]) -> list[Belief]:
    """Its lore: the views labelled a taste. A lived claim never is (A22)."""
    return [b for b in views if labels.get(b.id) is Kind.TASTE]


def lore_note(tastes: Iterable[str]) -> str | None:
    """The note that shows it a few of its own tastes, or None when there are none."""
    items = [t for t in tastes if t.strip()][:SHOWN]
    return _NOTE.render(items="\n".join(f"- {t}" for t in items)) if items else None
