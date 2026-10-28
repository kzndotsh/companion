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
    MemoryCandidate,
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
    Frame,
    Json,
    Provenance,
    RelationshipId,
    Speaker,
    Subject,
    Utterance,
)
from companion.prompts import get

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
STANCES = ("holds_view", "commits", "declines")

PROMPT = get("system/self-extract")
SYSTEM = PROMPT.text

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
                    "stance": {"type": "string", "enum": list(STANCES)},
                    "prompted": {"type": "boolean"},
                    "confirms": {"type": "string"},
                },
                "required": [
                    "ref",
                    "quote",
                    "claim",
                    "kind",
                    "confidence",
                    "grounding",
                    "stance",
                    "prompted",
                ],
            },
        }
    },
    "required": ["beliefs"],
}


def parse_views(data: Json) -> tuple[list[MemoryCandidate], list[Rejection]]:
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


def _view_problem(c: MemoryCandidate, source: Utterance | None) -> str | None:
    """Why this candidate must not become a view, or None if it passes the cheap checks."""
    if source is None:
        return "cited message not found and no single message holds the quote"
    checks = (
        (
            source.speaker is not Speaker.COMPANION,
            "a view must be quoted from the companion's own words",
        ),
        (
            c.kind not in SELF_KINDS or c.confidence < MIN_CONFIDENCE,
            "kind not allowed for a view, or too uncertain",
        ),
        (
            source.frame is not Frame.REAL,
            "said inside pretend, a story or a what-if, so not a view of its own",
        ),
        (
            c.grounding != "own_reasoning",
            f"not the companion's own view ({c.grounding or 'unlabelled'})",
        ),
        (
            c.stance == "declines" and c.prompted,
            "a refusal said in reply to something the user asked for, not a view it holds",
        ),
        (
            _AGREEING_OPENER.search(source.text) is not None,
            "stated in a message that opens by agreeing with the user",
        ),
    )
    return next((message for failed, message in checks if failed), None)


def to_view(
    c: MemoryCandidate,
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
