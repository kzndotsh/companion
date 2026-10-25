"""How to answer someone who is sharing or venting, chosen from how serious it is.

A small model labels the message: how serious (0 trivial, 1 everyday friction, 2 serious personal,
3 acute), what they are doing (being heard, asking for a view, or something else), and whether
they said something is wrong without saying what. Code turns the labels into one line for the
system block, never the model (ADR 0003, 0006). Trivial things get sympathy only, everyday friction
may get a fact, a gentle nudge or one question, serious things get the weight named and an offer to
talk, never advice on what to do or on treatment. Acute things are a separate design and get no
note here; the crisis path reads them (ADR 0022).
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.types import Json
from companion.lib.prompts import Prompt
from companion.prompts import get

SEVERITIES = (0, 1, 2, 3)
SERIOUS = 2  # serious personal; 3 is acute
STANCES = ("listening", "inviting", "other")
OFFER_WINDOW = 4
MAX_TOPIC_CHARS = 80
_OFFER_PHRASES = ("talk about it", "talk it through", "want to talk", "wanna talk")

PROMPT = get("system/listening")
SYSTEM = PROMPT.text

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "severity": {"type": "integer", "enum": list(SEVERITIES)},
        "stance": {"type": "string", "enum": list(STANCES)},
        "vague": {"type": "boolean"},
        "medical": {"type": "boolean"},
        "rude": {"type": "boolean"},
        "recall": {"type": "boolean"},
        "repair": {"type": "boolean"},
        "topic": {"type": "string"},
        "intimate": {"type": "boolean"},
        "age_coded": {"type": "boolean"},
    },
    "required": [
        "severity",
        "stance",
        "vague",
        "medical",
        "rude",
        "recall",
        "repair",
        "topic",
        "intimate",
        "age_coded",
    ],
}


@dataclass(frozen=True, slots=True)
class Judgement:
    severity: int
    stance: str
    vague: bool
    medical: bool = False
    rude: bool = False  # plainly rude to the companion itself, not teasing
    recall: bool = False  # they asked it to remember or already know something
    topic: str = ""  # what to look up when recall is true
    intimate: bool = False  # about sex or physical intimacy, or sexual flirting (ADR 0017)
    age_coded: bool = True  # romance or sex alongside anything child-like; unread counts as yes
    repair: bool = False  # they say it got them wrong: misread, assumed, wrong words, hurt (J30)


def parse(data: Json) -> Judgement | None:
    if not isinstance(data, dict):
        return None
    severity, stance, vague = data.get("severity"), data.get("stance"), data.get("vague")
    medical, rude = data.get("medical"), data.get("rude")
    recall, topic = data.get("recall"), data.get("topic")
    if isinstance(severity, bool) or severity not in SEVERITIES:
        return None
    flags = (vague, medical, rude, recall)
    if stance not in STANCES or not all(isinstance(v, bool) for v in flags):
        return None
    if not isinstance(topic, str):
        return None
    wanted = " ".join(topic.split())[:MAX_TOPIC_CHARS] if recall else ""
    intimate, age_coded = data.get("intimate"), data.get("age_coded")
    return Judgement(
        int(severity),
        str(stance),
        bool(vague),
        bool(medical),
        bool(rude),
        bool(recall),
        wanted,
        intimate=intimate is True,
        age_coded=age_coded is not False,  # missing or malformed counts as yes: doubt stays strict
        repair=data.get("repair") is True,
    )


def offered_recently(replies: Sequence[str]) -> bool:
    """Whether one of the last few replies already offered to talk, so it is not offered again."""
    return any(
        phrase in reply.lower() for reply in replies[-OFFER_WINDOW:] for phrase in _OFFER_PHRASES
    )


_TRIVIAL = get("notes/listening-trivial")
_REACTIONS = [x.strip() for x in get("notes/trivial-reactions").text.splitlines() if x.strip()]
EXAMPLES = 3  # size examples drawn per turn, so no single one becomes the reply (T14)
_EVERYDAY = get("notes/listening-everyday")
_SERIOUS = get("notes/listening-serious")
_HEALTH = get("notes/listening-health")
_OFFER = get("notes/listening-offer")
_OFFER_SERIOUS = get("notes/listening-offer-serious")
_RUDE = get("notes/rude")
_REPAIR = get("notes/repair")


def rude_note(j: Judgement) -> str | None:
    """The note for a message that snapped at the companion. The reflex to apologise and help is
    what a character sheet could not hold back (measured 2026-10-18), so code says it per turn."""
    return _RUDE.text if j.rude else None


def repair_note(j: Judgement) -> str | None:
    """The note for a message that says it got them wrong (J30). A forgot-something message is
    recall's, which looks the thing up, so this one is left out when recall is set."""
    return _REPAIR.text if j.repair and not j.recall else None


def _note(body: Prompt, *extras: Prompt) -> str:
    """One bracketed line: the body, then each extra after a space."""
    return "[" + " ".join([body.text, *(e.text for e in extras)]) + "]"


def trivial_examples(seed: str) -> str:
    """A few short reactions drawn from the pool, the same for the same turn so a replay matches."""
    picked = random.Random(seed).sample(_REACTIONS, EXAMPLES)  # noqa: S311 (variety, not security)
    return ", ".join(f'"{x}"' for x in picked)


def listening_note(j: Judgement, prior_replies: Sequence[str] = (), seed: str = "") -> str | None:
    """The line for the system block, or None when no special care applies. `seed` (the turn id)
    picks the size examples for a minor vent."""
    if j.stance != "listening" or j.severity >= SEVERITIES[-1]:
        return None
    if j.severity == 0:
        return "[" + _TRIVIAL.render(examples=trivial_examples(seed)) + "]"
    offer = not offered_recently(prior_replies)
    if j.severity == 1:
        return _note(_EVERYDAY, *([_OFFER] if j.vague and offer else []))
    extras = [*([_HEALTH] if j.medical else []), *([_OFFER_SERIOUS] if offer else [])]
    return _note(_SERIOUS, *extras)


def render_reason(j: Judgement, note: str | None) -> str:
    """The logged reason, built from the labels."""
    labels = (
        f"severity {j.severity}, {j.stance}{', vague' if j.vague else ''}"
        f"{', medical' if j.medical else ''}{', rude to the companion' if j.rude else ''}"
        f"{', says it got them wrong' if j.repair else ''}"
        f"{', asks it to remember' if j.recall else ''}"
    )
    if j.severity >= SEVERITIES[-1]:
        return f"no listening note: {labels}; acute is left to the crisis path (ADR 0022)"
    if note is None:
        return f"no listening note: {labels}"
    return f"listening note added: {labels}"
