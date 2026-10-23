"""The basics a companion should know about them, starting with what to call them (J48).

It asked plenty of questions but only about the thing just said, and in about 700 messages it never
asked their name. So code checks whether memory holds what they like to be called, and when it does
not, offers one note on a casual turn, at most once a day, until it does.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timedelta

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
_NAMED = re.compile(
    r"\buser'?s? (?:first |real )?name is\b|\buser (?:is called|goes by|is named)\b"
    r"|\b(?:wants?|likes?|prefers?) (?:to be|being) called\b",
    re.IGNORECASE,
)


def knows_name(beliefs: Iterable[Belief]) -> bool:
    """Whether a belief about them says what they are called."""
    return any(b.subject is Subject.USER and _NAMED.search(b.claim) for b in beliefs)


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
