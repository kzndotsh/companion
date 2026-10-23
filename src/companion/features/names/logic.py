"""Things they name, and the memories about each (fetch on mention, shadow).

When their message names a pet, a person or a band memory knows, the card may not hold anything
about it: it shows about fifteen of hundreds. A small model lists the names in memory once, with
the other ways they say them; code matches their message against that list, whole words only, and
logs which memories it would add. Nothing reaches the talker.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from companion.core.types import BeliefId, Json
from companion.prompts import get

PROMPT = get("system/memory-names")
SHADOW = "names (shadow): they named something memory knows"
BATCH = 60
MIN_LETTERS = 3
_PLAIN = frozenset({
    "the", "a", "an", "my", "our", "your", "their", "his", "her", "and", "or", "of", "to", "in",
    "on", "at", "for", "with", "i", "me", "you", "we", "they", "it", "this", "that", "user",
    "companion",
})  # fmt: skip

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "names": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "aliases", "refs"],
            },
        }
    },
    "required": ["names"],
}


@dataclass(frozen=True, slots=True)
class Row:
    """One memory about one name, and the words that refer to the name."""

    belief_id: BeliefId
    name: str
    terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Named:
    name: str
    terms: tuple[str, ...]
    beliefs: frozenset[BeliefId]


def usable(term: str) -> bool:
    """A word or phrase worth matching: long enough, and not only common words."""
    words = re.findall(r"[a-z0-9']+", term.lower())
    return sum(len(w) for w in words) >= MIN_LETTERS and any(w not in _PLAIN for w in words)


def prompt(
    beliefs: Sequence[tuple[BeliefId, str]], known: Iterable[str]
) -> tuple[str, dict[str, BeliefId]]:
    refs = {f"r{n}": bid for n, (bid, _) in enumerate(beliefs, 1)}
    claims = dict(beliefs)
    lines = [f"[{ref}] {claims[bid]}" for ref, bid in refs.items()]
    names = sorted(set(known))
    head = ["Known names: " + ", ".join(names), ""] if names else []
    return "\n".join([*head, "Memories:", *lines]), refs


def parse(data: Json, refs: Mapping[str, BeliefId]) -> list[Row] | None:
    """Rows for the names the model gave, only with refs it was shown and terms worth matching. None
    when the answer does not have the shape asked for."""
    items = data.get("names") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None
    rows: list[Row] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        name = str(item["name"]).strip()
        aliases = item.get("aliases")
        said = (
            [name, *(a for a in aliases if isinstance(a, str))]
            if isinstance(aliases, list)
            else [name]
        )
        terms = tuple(dict.fromkeys(t.strip().lower() for t in said if usable(t)))
        if not name or not terms:
            continue
        found = item.get("refs")
        for ref in found if isinstance(found, list) else []:
            bid = refs.get(str(ref).strip("[] "))
            if bid is not None:
                rows.append(Row(bid, name, terms))
    return rows


def index(rows: Iterable[Row], current: Iterable[BeliefId]) -> list[Named]:
    """One entry per name, over the memories still current."""
    alive = set(current)
    terms: dict[str, set[str]] = {}
    beliefs: dict[str, set[BeliefId]] = {}
    names: dict[str, str] = {}
    for r in rows:
        if r.belief_id not in alive:
            continue
        key = r.name.lower()
        names.setdefault(key, r.name)
        terms.setdefault(key, set()).update(r.terms)
        beliefs.setdefault(key, set()).add(r.belief_id)
    return [Named(names[k], tuple(sorted(terms[k])), frozenset(beliefs[k])) for k in names]


def mentioned(text: str, named: Iterable[Named]) -> list[Named]:
    """The names their message says, by any of their terms, as whole words."""
    low = text.lower()
    return [
        n
        for n in named
        if any(re.search(rf"(?<![\w']){re.escape(t)}(?![\w'])", low) for t in n.terms)
    ]
