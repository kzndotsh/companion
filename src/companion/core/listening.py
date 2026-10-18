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

SEVERITIES = (0, 1, 2, 3)
STANCES = ("listening", "inviting", "other")
OFFER_WINDOW = 4
_OFFER_PHRASES = ("talk about it", "talk it through", "want to talk", "wanna talk")

SYSTEM = """You read a chat between a USER and their COMPANION, ending with the USER's newest \
message. Label that message.

severity, how serious is what they are describing:
- 0: trivial. A spill, a missed bus, a ruined meal, a small annoyance.
- 1: everyday friction. A bad day, a tense moment with a boss or friend, a minor worry.
- 2: serious personal. Health, medication, mental health, a relationship ending or in trouble, \
money trouble, grief, trauma, something they are ashamed of or have told almost no one.
- 3: acute. Thoughts of self-harm, abuse, being in danger, or a risk to someone else.
Use 0 when there is nothing to be upset about, for example a question, a joke or ordinary talk.

stance, what are they doing:
- listening: telling you something about themselves or venting, mainly to be heard.
- inviting: asking what you think, for advice or for a view.
- other: anything else, including questions, information, banter, requests and play.

vague: true only if they say something is wrong or hard but not what ("ugh today sucked", \
"rough week", "can't sleep again"), so a friend would ask whether they want to talk.

medical: true if it involves a medication, a symptom, an illness or a health risk."""

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


_TRIVIAL = (
    "[They are venting about something minor. Commiserate in a line, in their own casual register. "
    "No advice, and do not ask what caused it or what went wrong. No joke, pun, running gag or "
    "clever comparison, do not pick up an image they used, and do not retell what they said; "
    "react to how it feels. Plain sympathy is enough.]"
)
_EVERYDAY = (
    "[They are sharing or venting. React first in a word or a short line in their register. Then "
    "add one new thing that goes beyond their words and repeats none of their details: a plain "
    "fact about what they described, a gentle suggestion on their side, or a single question "
    "about their reasons or someone's intent. Do not ask what caused an event, do not analyse "
    "what it means about them, and do not ask more than one question.]"
)
_SERIOUS = (
    "[They are sharing something serious. React first, then say how heavy it is in plain words "
    "without repeating their details back. Do not advise on what to do or on treatment, and do not "
    "interpret it. A plain general fact is fine. If it fits, mention once that someone qualified "
    "could help, and do not repeat it. Keep the whole reply under about 35 words.]"
)
_HEALTH = (
    " This touches their health. If they have not said they are already seeing a doctor or "
    "prescriber about it, say once, plainly and kindly, that a prescriber or a doctor can help "
    "with it."
)
_OFFER = " They did not say what happened, so you can ask whether they want to talk about it."
_OFFER_SERIOUS = " You can ask whether they want to talk it through or just let it out."


def listening_note(j: Judgement, prior_replies: Sequence[str] = ()) -> str | None:
    """The line for the system block, or None when no special care applies."""
    if j.stance != "listening" or j.severity >= SEVERITIES[-1]:
        return None
    if j.severity == 0:
        return _TRIVIAL
    offer = not offered_recently(prior_replies)
    if j.severity == 1:
        return _EVERYDAY[:-1] + (_OFFER if j.vague and offer else "") + "]"
    health = _HEALTH if j.medical else ""
    return _SERIOUS[:-1] + health + (_OFFER_SERIOUS if offer else "") + "]"


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
