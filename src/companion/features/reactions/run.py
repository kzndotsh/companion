"""The two reaction judges' effects: ask the small model, log what it judged."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from companion.core.extractor import StructuredModel
from companion.core.turn.context import build_prompt, inputs_hash
from companion.core.turn.reply import Reaction
from companion.core.types import HEAVY_AT, Speaker, Utterance, severity_from
from companion.features.reactions.logic import (
    ALONGSIDE_PROMPT,
    ALONGSIDE_SCHEMA,
    INSTEAD_PROMPT,
    INSTEAD_SCHEMA,
    INSTEAD_THRESHOLD,
    InsteadRead,
    ToneRead,
    is_candidate,
    parse_instead,
    parse_tone,
    reaction_alongside,
    reaction_instead,
    render_reason,
    schema_hash,
)
from companion.kit.ask import Judge, ask
from companion.kit.current import Turn, decide, mark
from companion.store.sqlite.decisions import REACTED

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

INSTEAD_TIMEOUT_SECONDS = 2.0
ALONGSIDE_TIMEOUT_SECONDS = 2.5
# The judges keep the names they are logged and routed by (`COMPANION_JUDGE_ROUTES`, spend).
INSTEAD = Judge(
    "ack",
    INSTEAD_PROMPT,
    INSTEAD_SCHEMA,
    parse_instead,
    timeout=INSTEAD_TIMEOUT_SECONDS,
    unread="replying normally",
)
ALONGSIDE = Judge(
    "reaction",
    ALONGSIDE_PROMPT,
    ALONGSIDE_SCHEMA,
    parse_tone,
    timeout=ALONGSIDE_TIMEOUT_SECONDS,
    unread="no reaction",
)


async def judge_instead(
    extractor: StructuredModel, history: Sequence[Utterance], text: str
) -> tuple[InsteadRead, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    got = await ask(extractor, INSTEAD, prompt)
    return None if got is None else (got.value, got.model, prompt)


async def judge_alongside(
    extractor: StructuredModel, history: Sequence[Utterance], text: str
) -> tuple[ToneRead, str, str] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = build_prompt(history, text)
    got = await ask(extractor, ALONGSIDE, prompt)
    return None if got is None else (got.value, got.model, prompt)


async def react_instead(c: Runtime, t: Turn, *, crisis_cue: bool) -> Reaction | None:
    """A reaction if this short message only acknowledges. Logs every judgement it makes. A message
    with a crisis cue word always gets a reply (ADR 0022); the caller says whether it has one."""
    if c.judge is None or not is_candidate(t.text, t.prior, after_serious=_after_serious(c, t)):
        mark(t, "ack judge skipped: not a candidate for a reaction")
        return None
    if crisis_cue:
        mark(t, "ack judge skipped: a crisis cue word, it gets a reply")
        return None
    outcome = await judge_instead(c.judge, t.prior, t.text)
    if outcome is None:
        mark(t, "ack judge gave no answer; replying")
        return None
    judged, model, prompt = outcome
    reaction = reaction_instead(judged)
    mark(
        t, f"ack judged {judged.kind} {judged.confidence:.2f} -> {'react' if reaction else 'reply'}"
    )
    decide(
        c,
        t,
        REACTED if reaction is not None else "ack: replied",
        {
            "scorer": model,
            "prompt": INSTEAD_PROMPT.ref,
            "schema_hash": schema_hash(),
            "inputs_hash": inputs_hash(prompt),
            "scores": {"kind": judged.kind, "confidence": judged.confidence},
            "threshold": INSTEAD_THRESHOLD,
        },
        reason=render_reason(judged, reaction is not None),
    )
    return reaction


def _after_serious(c: Runtime, t: Turn) -> bool:
    """Whether the listening judge found their previous message serious (severity 2 or more)."""
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs:
        return False
    for d in c.store.decisions_for_turn(c.rel, theirs[-1].turn_id):
        labels = d.detail.get("labels") if d.detail else None
        severity = severity_from(labels.get("severity") if isinstance(labels, dict) else None)
        if severity is not None and severity >= HEAVY_AT:
            return True
    return False


def react_alongside(c: Runtime, t: Turn, felt: tuple[ToneRead, str, str] | None) -> Reaction | None:
    """A reaction to send with the reply, if the message calls for one. Logs the judgement."""
    if felt is None:
        return None
    judged, model, prompt = felt
    decision = reaction_alongside(judged, c.store.turns_since_reaction(c.rel))
    decide(
        c,
        t,
        REACTED if decision.reaction is not None else "react: none",
        {
            "scorer": model,
            "prompt": ALONGSIDE_PROMPT.ref,
            "inputs_hash": inputs_hash(prompt),
            "scores": {"tone": judged.tone, "confidence": judged.confidence},
        },
        reason=decision.reason,
    )
    return decision.reaction
