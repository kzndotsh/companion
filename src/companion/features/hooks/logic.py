"""A light question about a basic fact when their own words touch it (J48, the hook).

"I'm getting old" is the moment to ask how old they are; a question out of the blue is an interview.
Follow-up questions on what someone just said make people better liked (Huang et al. 2017); a
question about a basic memory already holds, or one asked again and again, does not. So a small
model says which basic their message touches; code asks only on a casual turn, at most one a day,
each basic at most twice, and only when the recall look-up finds nothing on it in memory. Shadow for
now: it only logs.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from enum import StrEnum

from companion.core.types import Json
from companion.lib.vote import unanimous
from companion.prompts import get

PROMPT = get("system/basics-hook")
WOULD_ASK = "hook (shadow): would ask about a basic their words touched"
EVERY = timedelta(hours=24)
MAX_OFFERS = 2


class Basic(StrEnum):
    WORK = "work"
    HOME = "home"
    PLACE = "place"
    AGE = "age"


SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"basic": {"type": "string", "enum": [*(b.value for b in Basic), "none"]}},
    "required": ["basic"],
}

# What the recall look-up searches memory for, to tell whether the basic is already known.
TOPIC = {
    Basic.AGE: "how old they are or their birthday",
    Basic.WORK: "what they do for work or school, or that they are looking for work",
    Basic.HOME: "who they live with",
    Basic.PLACE: "where they live now",
}
KNEW = "hook (shadow): memory already holds the basic their words touched"


def read_basic(data: Json) -> Basic | None:
    value = data.get("basic") if isinstance(data, dict) else None
    return Basic(value) if isinstance(value, str) and value in set(Basic) else None


def agreed(reads: Iterable[Basic | None]) -> Basic | None:
    """The basic every read named, else None."""
    return unanimous(reads)


def may_ask(basic: Basic | None, asked: Iterable[tuple[str, datetime]], now: datetime) -> bool:
    """Whether the gate allows a question: a basic their words touched, no hook in the last day, and
    this basic offered fewer than MAX_OFFERS times. `asked` is (basic, when) of past hooks. Whether
    memory already holds it is the recall look-up's to say."""
    if basic is None:
        return False
    past = list(asked)
    if any(now - at < EVERY for _, at in past):
        return False
    return sum(b == basic for b, _ in past) < MAX_OFFERS
