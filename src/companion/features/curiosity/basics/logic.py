"""The basics a companion should know about them: what to call them, then their pronouns (J48).

It asked plenty of questions but only about the thing just said, and in about 700 messages it never
asked their name. So code checks whether memory holds what they like to be called, and when it does
not, offers one note on a casual turn, at most once a day, until it does. Once the name is known,
the same goes for how they want to be referred to, which is a setting (`core/turn/address.py`).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timedelta

from companion.core.turn.address import names_them
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Evidence,
    Json,
    Provenance,
    Speaker,
    Subject,
    Utterance,
)
from companion.prompts import get

ASK_NAME = get("notes/ask-name")
ASK_EVERY = timedelta(hours=24)
ASKED = "basics: offered to ask what to call them"


def knows_name(beliefs: Iterable[Belief]) -> bool:
    """Whether a belief about them says what they are called."""
    return any(names_them(b) for b in beliefs)


def ask_name(*, known: bool, casual: bool, asked_recently: bool) -> str | None:
    """The note for this turn, or None."""
    return None if known or not casual or asked_recently else ASK_NAME.text


NAME_CAPTURE = get("system/name-capture")
NAME_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
}
MAX_NAME_WORDS = 3
_ASKED_FOR_NAME = re.compile(
    r"\byour name\b|\bcall you\b|\b(?:like|love|want|prefer)s? (?:being|to be) called\b",
    re.IGNORECASE,
)


def asked_for_name(reply: str) -> bool:
    """Whether the companion's message asked what to call them."""
    return "?" in reply and _ASKED_FOR_NAME.search(reply) is not None


def parse_name(data: Json, said: str) -> str | None:
    """The name they gave, only if it is short and appears in what they wrote."""
    if not isinstance(data, dict):
        return None
    name = data.get("name")
    if not isinstance(name, str):
        return None
    name = " ".join(name.split()).strip(".,!?\"'")
    if not name or len(name.split()) > MAX_NAME_WORDS or name.lower() not in said.lower():
        return None
    return name


def name_belief(said: Utterance, name: str, belief_id: str, now: datetime) -> Belief:
    """A memory of what they like to be called, quoting their own answer (ADR 0001)."""
    return Belief(
        id=BeliefId(belief_id),
        relationship_id=said.relationship_id,
        subject=Subject.USER,
        kind=BeliefKind.TRAIT,
        claim=f"The user's name is {name}.",
        evidence=(Evidence(said.id, said.text),),
        provenance=Provenance.STATED,
        speaker=Speaker.USER,
        frame=said.frame,
        confidence=0.9,
        valid_from=said.at,
        recorded_at=now,
        sensitivity=0,
    )


ASK_PRONOUNS = get("notes/ask-pronouns")
ASKED_PRONOUNS = "basics: offered to ask their pronouns"


def ask_pronouns(
    *, address_set: bool, name_known: bool, casual: bool, name_asked: bool, asked_recently: bool
) -> str | None:
    """The pronoun note for this turn, or None. The name comes first: pronouns only once it is
    known, and not within a day of asking it (`name_asked`), so the two never share a turn."""
    if address_set or not name_known or not casual or name_asked or asked_recently:
        return None
    return ASK_PRONOUNS.text


PRONOUN_CAPTURE = get("system/pronoun-capture")
PRONOUN_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"pronouns": {"type": "string"}},
    "required": ["pronouns"],
}
MAX_PRONOUN_CHARS = 30
_ASKED_FOR_PRONOUNS = re.compile(
    r"\bpronouns?\b|\bshe or he\b|\bhe or she\b|\bhe or they\b|\bshe or they\b"
    r"|\brefer to you\b|\breferred to\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)?")


def asked_for_pronouns(reply: str) -> bool:
    """Whether the companion's message asked which pronouns they use."""
    return "?" in reply and _ASKED_FOR_PRONOUNS.search(reply) is not None


def parse_pronouns(data: Json, said: str) -> str | None:
    """The pronouns they gave, only if short and every word of it is in what they wrote, ignoring
    case and slashes."""
    if not isinstance(data, dict):
        return None
    got = data.get("pronouns")
    if not isinstance(got, str):
        return None
    got = " ".join(got.split()).strip(".,!?\"'")
    words = _WORD.findall(got.lower())
    theirs = set(_WORD.findall(said.lower()))
    if not words or len(got) > MAX_PRONOUN_CHARS or not set(words) <= theirs:
        return None
    return got
