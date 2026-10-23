"""What kind of memory it is: about their life, a remark about the bot, or a routine moment.

The memory pass kept remarks about the companion itself ("you ask a question every turn", a feature
being added) and one day's routine (a particular dinner) as lasting facts about them. The owner set
the rule: remarks about the bot are dropped, a routine moment lasts a week, and when it is unclear
they are asked. A small model labels each memory against a written definition with its exceptions
(how they want to be treated, their feelings about it, building it as part of their life, the
habit behind a routine, anything with a feeling, a first or an ongoing matter) three times; code
acts only when all three agree, and asks the owner otherwise.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from enum import StrEnum

from companion.core.types import Json
from companion.lib.vote import unanimous
from companion.prompts import get

PROMPT = get("system/memory-worth")
ROUTINE_DAYS = timedelta(days=7)


class Label(StrEnum):
    KEEP = "keep"
    ABOUT_THE_BOT = "about_the_bot"
    ROUTINE = "routine"
    UNSURE = "unsure"


# what is stored for a memory already kept: the owner is asked instead of code acting
ASK_ABOUT_THE_BOT = "ask_about_the_bot"
ASK_ROUTINE = "ask_routine"
ASKED = (ASK_ABOUT_THE_BOT, ASK_ROUTINE, Label.UNSURE.value)

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"label": {"type": "string", "enum": [x.value for x in Label]}},
    "required": ["label"],
}


def read(data: Json) -> str | None:
    value = data.get("label") if isinstance(data, dict) else None
    return value if isinstance(value, str) and value in set(Label) else None


def verdict(reads: Sequence[str | None]) -> str:
    """keep, about_the_bot or routine when every read agrees; unsure when any read says other than
    keep without agreement; keep when the reads failed (nothing is acted on)."""
    agreed = unanimous(reads)
    if agreed is not None:
        return agreed
    if any(r is not None and r != Label.KEEP for r in reads):
        return Label.UNSURE.value
    return Label.KEEP.value


def to_ask(found: str) -> str:
    """For a memory kept before the rule: an agreed change becomes a question instead."""
    return {Label.ABOUT_THE_BOT.value: ASK_ABOUT_THE_BOT, Label.ROUTINE.value: ASK_ROUTINE}.get(
        found, found
    )
