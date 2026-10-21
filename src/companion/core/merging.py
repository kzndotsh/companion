"""Memories about one thing, proposed as one (ADR 0019).

The memory pass often splits one moment into pieces (one appointment became six memories) and
restates an interest in new words (three memories of one hobby). A small model groups the
memories about one thing three times; a group counts only where all three reads put each pair of
its members together. Another writes the merged wording, keeping every detail. Nothing is merged
without the owner: each group is a question in `companion memory review`.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence

from companion.core.agreement import READS
from companion.core.types import Belief, BeliefKind, Json
from companion.prompts import get

GROUP = get("system/memory-group")
WRITE = get("system/memory-merge")
PROPOSED = "memory: proposed merging memories about one thing"
NOTE = "note: "  # an owner's note on a merge question; it stays open
PICK = "pick "  # the members the owner said belong together, by number, proposed again alone

GROUP_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "groups": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}
    },
    "required": ["groups"],
}
WRITE_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"claim": {"type": "string"}, "keep_apart": {"type": "boolean"}},
    "required": ["claim", "keep_apart"],
}

Group = frozenset[int]


def listing(beliefs: Sequence[Belief]) -> str:
    return "\n".join(
        f"[m{i}] ({b.recorded_at.date().isoformat()}) {b.claim}"
        f'  | their words: "{b.evidence[0].quote}"'
        for i, b in enumerate(beliefs, start=1)
    )


def read_groups(data: Json, size: int) -> list[Group] | None:
    """The groups in one read, as positions in the listing; None when the answer is malformed."""
    raw = data.get("groups") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    found: list[Group] = []
    for g in raw:
        if not isinstance(g, list):
            continue
        labels = (str(x).strip().strip("[]").removeprefix("m") for x in g)
        members = frozenset(int(x) - 1 for x in labels if x.isdigit() and 0 < int(x) <= size)
        if len(members) > 1:
            found.append(members)
    return found


def agreed(reads: Sequence[list[Group] | None]) -> list[Group]:
    """The groups every read agrees on: pairs that all reads put together, joined into groups. A
    failed read is never agreement."""
    if len(reads) != READS or any(r is None for r in reads):
        return []
    together: list[set[tuple[int, int]]] = [
        {pair for g in r for pair in itertools.combinations(sorted(g), 2)} for r in reads if r
    ]
    if len(together) != READS:
        return []
    pairs: set[tuple[int, int]] = together[0].intersection(*together[1:])
    groups: list[set[int]] = []
    for a, b in sorted(pairs):
        joined = [g for g in groups if a in g or b in g]
        merged: set[int] = {a, b}.union(*joined)
        groups = [g for g in groups if g not in joined] + [merged]
    return sorted((frozenset(g) for g in groups), key=min)


def read_claim(data: Json) -> str | None:
    """The merged wording, or None when the writer said to keep them apart."""
    if not isinstance(data, dict) or data.get("keep_apart") is True:
        return None
    claim = data.get("claim")
    return " ".join(claim.split()) if isinstance(claim, str) and claim.strip() else None


def merged_kind(members: Sequence[Belief]) -> BeliefKind:
    """A merge that holds a passing state keeps fading like one; otherwise the first member's."""
    kinds = [b.kind for b in members]
    return BeliefKind.STATE if BeliefKind.STATE in kinds else kinds[0]
