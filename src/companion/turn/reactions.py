"""The two reaction judges' effects: ask the small model, log what it judged."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from companion.core.extractor import StructuredModel
from companion.core.turn.context import Scored, conversation_prompt
from companion.core.turn.listening import logged_heavy
from companion.core.turn.reactions import (
    ALONGSIDE_PROMPT,
    ALONGSIDE_SCHEMA,
    INSTEAD_PROMPT,
    INSTEAD_SCHEMA,
    INSTEAD_THRESHOLD,
    NO_REACTION,
    REACTED,
    REPLIED,
    InsteadRead,
    ToneRead,
    is_candidate,
    parse_instead,
    parse_tone,
    reaction_alongside,
    reaction_instead,
    render_reason,
)
from companion.core.turn.reply import Reaction
from companion.core.types import Speaker, Utterance
from companion.kit.ask import Judge, ask
from companion.kit.current import Turn, decide, mark

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
) -> Scored[InsteadRead] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = conversation_prompt(history, text)
    got = await ask(extractor, INSTEAD, prompt)
    return None if got is None else Scored(got.value, got.model, prompt)


async def judge_alongside(
    extractor: StructuredModel, history: Sequence[Utterance], text: str
) -> Scored[ToneRead] | None:
    """The judgement, the model id and the prompt, or None if it could not be made in time."""
    prompt = conversation_prompt(history, text)
    got = await ask(extractor, ALONGSIDE, prompt)
    return None if got is None else Scored(got.value, got.model, prompt)


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
    judged = outcome.read
    reaction = reaction_instead(judged)
    mark(
        t, f"ack judged {judged.kind} {judged.confidence:.2f} -> {'react' if reaction else 'reply'}"
    )
    decide(
        c,
        t,
        REACTED if reaction is not None else REPLIED,
        outcome.detail(
            INSTEAD_PROMPT.ref,
            schema=INSTEAD_SCHEMA,
            scores={"kind": judged.kind, "confidence": judged.confidence},
            threshold=INSTEAD_THRESHOLD,
        ),
        reason=render_reason(judged, reaction is not None),
    )
    return reaction


def _after_serious(c: Runtime, t: Turn) -> bool:
    """Whether the listening judge found their previous message serious (severity 2 or more)."""
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs:
        return False
    return any(
        logged_heavy(d.detail) for d in c.store.decisions_for_turn(c.rel, theirs[-1].turn_id)
    )


def react_alongside(c: Runtime, t: Turn, felt: Scored[ToneRead] | None) -> Reaction | None:
    """A reaction to send with the reply, if the message calls for one. Logs the judgement."""
    if felt is None:
        return None
    judged = felt.read
    decision = reaction_alongside(judged, c.store.turns_since_reaction(c.rel))
    decide(
        c,
        t,
        REACTED if decision.reaction is not None else NO_REACTION,
        felt.detail(
            ALONGSIDE_PROMPT.ref, scores={"tone": judged.tone, "confidence": judged.confidence}
        ),
        reason=decision.reason,
    )
    return decision.reaction
