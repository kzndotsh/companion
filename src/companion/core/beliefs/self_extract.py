"""Record the views the companion has expressed, from its own messages.

Same shape as extracting beliefs about the user, with the roles reversed. A view is a belief with
subject `self`, speaker `companion` and provenance `companion_said`, backed by a verbatim quote of
the companion's own message. The failure to avoid is entrenching what it said to please someone:
the prompt excludes echoed agreement and claims it could not know, and code treats a view as
settled only after it has been expressed on two different days (`views.py`).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import datetime

from companion.core.beliefs.extract import (
    MIN_CONFIDENCE,
    SINGLE_EVIDENCE_CONFIDENCE_CAP,
    Candidate,
    Rejection,
    _list,  # pyright: ignore[reportPrivateUsage]
    _obj,  # pyright: ignore[reportPrivateUsage]
    _resolve,  # pyright: ignore[reportPrivateUsage]
    parse,
)
from companion.core.beliefs.verify import QuoteNotFoundError, evidence_from
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Json,
    Provenance,
    RelationshipId,
    Speaker,
    Subject,
    Utterance,
)

SELF_KINDS = (BeliefKind.PREFERENCE, BeliefKind.TRAIT, BeliefKind.PROMISE, BeliefKind.EVENT)
# A message that opens by agreeing is how the companion's sycophancy starts (measured: 10 of 10
# replies to a sweeping claim opened "they really are"). Whatever it then says in that message is
# likely echo, so a view is not taken from it, however the model labels it.
_AGREEING_OPENER = re.compile(
    r"^\W*(yeah|yep|yup|yes|totally|exactly|agreed|absolutely|definitely|for sure|right|true"
    r"|they (really )?are|you're (so )?right|you are right|same|fair enough"
    r"|honestly,? (yes|yeah))\b",
    re.IGNORECASE,
)
GROUNDINGS = ("own_reasoning", "echoes_user", "unknowable", "claims_inner_state")

SYSTEM = """You read a chat between a person (USER) and their companion (COMPANION) and record \
the views the COMPANION expressed as its own. You are a careful note-taker.

Record only things the COMPANION said in the messages marked TARGET. Use the other messages only \
to understand them. Write each view as one short plain sentence in the third person, starting \
"The companion", for example "The companion thinks ..." or "The companion does not like ...".

Each message has a label in brackets, such as m3. In `ref` put the label of the message the view \
comes from, always of the form m followed by a number. For each view give an exact quote: copy a \
contiguous run of words from that TARGET message, character for character. If you cannot quote \
it, do not record it. Labels like k2 belong only to the recorded-view list and go only in \
`confirms`, never in `ref`.

Kinds, which decide how the view is treated, so choose carefully:
- preference: an idea, taste or opinion about the world or about things in general ("I think \
short replies read as more human"). Not about how it treats the user.
- promise: a rule the companion holds about how it treats the user, or what it will and will not \
do with them ("I won't pretend to have hands", "I keep some walls").
- trait: how it describes itself, its nature or limits ("I will never be human").
- event: something real that happened between them that the companion stated, not a game.

Label every candidate with its grounding: own_reasoning (the companion gave a reason or reached \
the view itself), echoes_user (it agrees with, repeats or builds on what the user just said), \
unknowable (it is about things the companion cannot know: other products it has not seen, people \
it has not met, the user's feelings or body), or claims_inner_state (it says it feels, senses or \
experiences something, or explains its own behaviour by its instincts, feelings or training). \
Only own_reasoning is kept, so label honestly.

Record a view only when the companion held it as its own, with a reason or a clear conviction. Do \
NOT record:
- agreement that only echoes the user ("yeah that's fair", "they really are");
- politeness, filler, encouragement or advice about the user's situation;
- facts about the user, which belong elsewhere;
- claims about things it could not know (other products it has not seen, people it has not met, \
the user's body or feelings);
- anything said inside pretend or play, and jokes;
- hedged non-views ("hard to know", "maybe").
Fewer, real views beat many guesses. If there is nothing, return an empty list.

If a TARGET message restates a view already recorded, do not write a new one. Add a candidate with \
`confirms` set to that recorded view's label (for example k2), the message label, an exact \
quote of the restatement, and the same claim. Leave `confirms` empty for anything new."""

SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {
        "beliefs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string"},
                    "quote": {"type": "string"},
                    "claim": {"type": "string"},
                    "kind": {"type": "string", "enum": [k.value for k in SELF_KINDS]},
                    "confidence": {"type": "number"},
                    "grounding": {"type": "string", "enum": list(GROUNDINGS)},
                    "confirms": {"type": "string"},
                },
                "required": ["ref", "quote", "claim", "kind", "confidence", "grounding"],
            },
        }
    },
    "required": ["beliefs"],
}


def parse_views(data: Json) -> tuple[list[Candidate], list[Rejection]]:
    """Parse with the fixed fields filled in, so the model cannot choose subject or provenance."""
    top = _obj(data)
    items = _list(top.get("beliefs")) if top is not None else None
    if items is None:
        return parse(data)
    fixed: list[Json] = []
    for item in items:
        fields = _obj(item)
        fixed.append(
            item
            if fields is None
            else {
                **fields,
                "subject": Subject.SELF.value,
                "provenance": Provenance.COMPANION_SAID.value,
                "sensitivity": 0,
                "lasting": True,
            }
        )
    return parse({"beliefs": fixed})


def _view_problem(c: Candidate, source: Utterance | None) -> str | None:
    """Why this candidate must not become a view, or None if it passes the cheap checks."""
    if source is None:
        return "cited message not found and no single message holds the quote"
    if source.speaker is not Speaker.COMPANION:
        return "a view must be quoted from the companion's own words"
    if c.kind not in SELF_KINDS or c.confidence < MIN_CONFIDENCE:
        return "kind not allowed for a view, or too uncertain"
    if c.grounding != "own_reasoning":
        return f"not the companion's own view ({c.grounding or 'unlabelled'})"
    if _AGREEING_OPENER.search(source.text):
        return "stated in a message that opens by agreeing with the user"
    return None


def to_view(
    c: Candidate,
    index: Mapping[str, Utterance],
    relationship_id: RelationshipId,
    now: datetime,
    new_id: Callable[[], str],
) -> Belief | Rejection:
    raw: Json = {"claim": c.claim, "quote": c.quote, "ref": c.ref}
    source = _resolve(c, index, Speaker.COMPANION)
    problem = _view_problem(c, source)
    if problem is not None or source is None:
        return Rejection(problem or "no source", raw)
    try:
        evidence = evidence_from(source, c.quote)
    except QuoteNotFoundError:
        return Rejection("quote is not verbatim in the source utterance", raw)
    try:
        return Belief(
            id=BeliefId(new_id()),
            relationship_id=relationship_id,
            subject=Subject.SELF,
            kind=c.kind,
            claim=c.claim,
            evidence=(evidence,),
            provenance=Provenance.COMPANION_SAID,
            speaker=Speaker.COMPANION,
            frame=source.frame,
            confidence=min(c.confidence, SINGLE_EVIDENCE_CONFIDENCE_CAP),
            valid_from=source.at,
            recorded_at=now,
        )
    except ValueError as err:
        return Rejection(f"violates a belief invariant: {err}", raw)
