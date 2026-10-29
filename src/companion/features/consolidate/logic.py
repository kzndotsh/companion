"""Keeping memory tidy without deciding what the person is (ADR 0019).

A judge reads a memory, or two memories, three times. Code acts on its own only where the judge,
read the same way all three times, matched the owner's own review: a passing moment that has
already faded from the card is closed, and a new memory that is the same as an existing one becomes
evidence on it. Every other finding becomes a question for the owner. Nothing is merged
automatically.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from companion.core.types import Belief, Json
from companion.lib.vote import unanimous
from companion.prompts import get

HELD = 2  # sensitive memories are only ever the owner's call
CHECK = get("system/memory-check")
# Every name the check's prompt has had, so a rename keeps what it already read.
CHECK_NAMES = ("system/memory-check",)
PAIR = get("system/memory-pair")


class Label(StrEnum):
    KEEP = "keep"
    PASSING = "passing"
    OUT_OF_DATE = "out_of_date"
    OVERSTATED = "overstated"


class Relation(StrEnum):
    SAME = "same"
    MERGE = "merge"
    DISTINCT = "distinct"
    REPLACES = "replaces"
    CONTRADICTS = "contradicts"


MIXED = "mixed"
ASK_OWNER = frozenset({Label.OUT_OF_DATE, Label.OVERSTATED})
CHECK_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"label": {"type": "string", "enum": [x.value for x in Label]}},
    "required": ["label"],
}
PAIR_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"relation": {"type": "string", "enum": [x.value for x in Relation]}},
    "required": ["relation"],
}


def read_label(data: Json) -> str | None:
    value = data.get("label") if isinstance(data, dict) else None
    return value if isinstance(value, str) and value in set(Label) else None


def read_relation(data: Json) -> str | None:
    value = data.get("relation") if isinstance(data, dict) else None
    return value if isinstance(value, str) and value in set(Relation) else None


def verdict(reads: Sequence[str | None]) -> str:
    """The label when every read agrees, else MIXED. A failed read is never agreement."""
    return unanimous(reads) or MIXED


def check_prompt(b: Belief, today: str) -> str:
    return f"Today is {today}.\nMemory: {b.claim}"


def pair_prompt(older: Belief, newer: Belief) -> str:
    return f"Memory 1 (earlier): {older.claim}\nMemory 2 (later): {newer.claim}"


@dataclass(frozen=True, slots=True)
class Plan:
    """What code does with one memory's check: close it, ask the owner, or nothing."""

    close: bool = False
    ask: bool = False


def plan_for(b: Belief, found: str, *, faded: bool) -> Plan:
    if b.sensitivity >= HELD:
        return Plan(ask=found in ASK_OWNER or found == Label.PASSING)
    if found == Label.PASSING and faded:
        return Plan(close=True)
    return Plan(ask=found in ASK_OWNER)


def same_as(found: str) -> bool:
    """A new memory that every read calls the same as an existing one becomes evidence on it."""
    return found == Relation.SAME
