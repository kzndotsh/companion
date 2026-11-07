"""Memories about one thing, proposed as one (ADR 0019).

The memory pass often splits one moment into pieces (one appointment became six memories) and
restates an interest in new words (three memories of one hobby). A small model groups the
memories about one thing three times; a group counts only where all three reads put each pair of
its members together. Another writes the merged wording, keeping every detail. Nothing is merged
without the owner: each group is a question in `companion memory review`.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Sequence

from companion.core.types import Belief, BeliefKind, Json
from companion.lib.vote import READS
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


def read_wording(data: Json) -> str | None:
    """The merged wording, empty when the writer said to keep them apart or gave none, None when
    the answer was not an object."""
    return read_claim(data) or "" if isinstance(data, dict) else None


def merged_kind(members: Sequence[Belief]) -> BeliefKind:
    """A merge that holds a passing state keeps fading like one; otherwise the first member's."""
    kinds = [b.kind for b in members]
    return BeliefKind.STATE if BeliefKind.STATE in kinds else kinds[0]


# What a merged wording may not do on its own (2026-11-02: five readers judged 71 proposals, and 21
# wordings added a name, a time or a title never said, or dropped the date that kept a one-off a
# one-off). Checked in code; a wording that fails keeps one of the members' own sentences instead.
_DATED = re.compile(r"\b20\d\d-\d\d-\d\d\b")
_SPECIFIC = re.compile(r"[A-Za-z0-9][\w'\u2019.:-]*")
_SENTENCE_START = frozenset({"the", "on", "as", "they", "their", "in", "at", "a", "an", "since"})


def unsupported(claim: str, members: Sequence[Belief]) -> list[str]:
    """The names, numbers and dates in a merged wording that no member's claim or quote has, and
    the dates the members name that the wording dropped."""
    said = " ".join([b.claim for b in members] + [e.quote for b in members for e in b.evidence])
    source = said.lower()
    added = [
        tok.rstrip(".:-")
        for i, tok in enumerate(_SPECIFIC.findall(claim))
        if (any(ch.isdigit() for ch in tok) or (tok[0].isupper() and i > 0))
        and tok.lower() not in _SENTENCE_START
        and tok.rstrip(".:-").lower() not in source
    ]
    dropped = sorted(
        {d for b in members for d in _DATED.findall(b.claim)} - set(_DATED.findall(claim))
    )
    return added + [f"dropped {d}" for d in dropped]


def kept_wording(members: Sequence[Belief]) -> str:
    """The fullest of the members' own sentences, of the kind the merged memory takes."""
    kind = merged_kind(members)
    return max((b for b in members if b.kind is kind), key=lambda b: len(b.claim)).claim
