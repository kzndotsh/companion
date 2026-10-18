"""How to answer someone who is sharing or venting, chosen from how serious it is.

A small model labels the message: how serious (0 trivial, 1 everyday friction, 2 serious personal,
3 acute), what they are doing (being heard, asking for a view, or something else), and whether
they said something is wrong without saying what. Code turns the labels into one line for the
system block, never the model (ADR 0003, 0006). Trivial things get sympathy only, everyday friction
may get a fact, a gentle nudge or one question, serious things get the weight named and an offer to
talk, never advice on what to do or on treatment. Acute things are a separate design and get no
note here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from companion.core.types import Json
from companion.prompts import Prompt, get

SEVERITIES = (0, 1, 2, 3)
SERIOUS = 2  # serious personal; 3 is acute
STANCES = ("listening", "inviting", "other")
OFFER_WINDOW = 4
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
    },
    "required": ["severity", "stance", "vague", "medical"],
}


@dataclass(frozen=True, slots=True)
class Judgement:
    severity: int
    stance: str
    vague: bool
    medical: bool = False


def parse(data: Json) -> Judgement | None:
    if not isinstance(data, dict):
        return None
    severity, stance, vague = data.get("severity"), data.get("stance"), data.get("vague")
    medical = data.get("medical")
    if isinstance(severity, bool) or severity not in SEVERITIES:
        return None
    if stance not in STANCES or not isinstance(vague, bool) or not isinstance(medical, bool):
        return None
    return Judgement(int(severity), str(stance), vague, medical)


def offered_recently(replies: Sequence[str]) -> bool:
    """Whether one of the last few replies already offered to talk, so it is not offered again."""
    return any(
        phrase in reply.lower() for reply in replies[-OFFER_WINDOW:] for phrase in _OFFER_PHRASES
    )


_TRIVIAL = get("notes/listening-trivial")
_EVERYDAY = get("notes/listening-everyday")
_SERIOUS = get("notes/listening-serious")
_HEALTH = get("notes/listening-health")
_OFFER = get("notes/listening-offer")
_OFFER_SERIOUS = get("notes/listening-offer-serious")


def _note(body: Prompt, *extras: Prompt) -> str:
    """One bracketed line: the body, then each extra after a space."""
    return "[" + " ".join([body.text, *(e.text for e in extras)]) + "]"


def listening_note(j: Judgement, prior_replies: Sequence[str] = ()) -> str | None:
    """The line for the system block, or None when no special care applies."""
    if j.stance != "listening" or j.severity >= SEVERITIES[-1]:
        return None
    if j.severity == 0:
        return _note(_TRIVIAL)
    offer = not offered_recently(prior_replies)
    if j.severity == 1:
        return _note(_EVERYDAY, *([_OFFER] if j.vague and offer else []))
    extras = [*([_HEALTH] if j.medical else []), *([_OFFER_SERIOUS] if offer else [])]
    return _note(_SERIOUS, *extras)


def render_reason(j: Judgement, note: str | None) -> str:
    """The logged reason, built from the labels."""
    labels = (
        f"severity {j.severity}, {j.stance}{', vague' if j.vague else ''}"
        f"{', medical' if j.medical else ''}"
    )
    if j.severity >= SEVERITIES[-1]:
        return f"no listening note: {labels}; acute needs its own design (no crisis path yet)"
    if note is None:
        return f"no listening note: {labels}"
    return f"listening note added: {labels}"
