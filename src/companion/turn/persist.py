"""Their message for a turn, stored in exactly one place (the persist stage of a turn)."""

from __future__ import annotations

import contextlib
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import TYPE_CHECKING

from companion.core.frames import (
    MIN_CONFIDENCE as FRAME_MIN_CONFIDENCE,
)
from companion.core.frames import PROMPT as FRAMES_PROMPT
from companion.core.frames import (
    Judgement,
    companion_frame,
)
from companion.core.frames import render_reason as frame_reason
from companion.core.frames import resolve as frame_resolve
from companion.core.prompt.request import request_sha256
from companion.core.replay import TurnRecord
from companion.core.talker import Reply
from companion.core.turn.ack import (
    ReactAndReply,
    Reaction,
    inputs_hash,
)
from companion.core.turn.react import PROMPT as REACT_PROMPT
from companion.core.turn.react import Judgement as ReactJudgement
from companion.core.turn.react import decide as decide_reaction
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    Speaker,
    Utterance,
    UtteranceId,
)
from companion.core.views import why
from companion.loops.current import Turn, decide, mark, recorder
from companion.registry import FEATURES
from companion.store.sqlite.decisions import REACTED
from companion.turn.assemble import Assembled, CardLog
from companion.turn.frames import inputs_hash as frames_inputs_hash
from companion.turn.frames import schema_hash as frames_schema_hash
from companion.turn.mention import read_met
from companion.turn.values import Answered

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.turn")


def store_user(c: Conversation, t: Turn, channel: str, frame: Frame) -> Utterance:
    said = Utterance(
        UtteranceId(uuid.uuid4().hex),
        c.rel,
        t.session,
        t.turn,
        Speaker.USER,
        t.text,
        frame,
        channel,
        t.now,
    )
    c.store.append_utterance(said)
    return said


class TheirMessage:
    """Their message for this turn, stored exactly once: with the frame the turn resolved, or, if
    the turn fails before that, as real when the guard closes."""

    def __init__(self, c: Conversation, t: Turn, channel: str) -> None:
        self.c, self.t, self.channel = c, t, channel
        self.said: Utterance | None = None

    def store(self, frame: Frame) -> Utterance:
        if self.said is None:
            self.said = store_user(self.c, self.t, self.channel, frame)
        return self.said


@contextlib.asynccontextmanager
async def their_message(c: Conversation, t: Turn, channel: str) -> AsyncGenerator[TheirMessage]:
    """The one place their message is stored. A turn that fails at any stage still keeps it, as
    real, and the failure goes on up; before, an error in the look-ups or the card lost it."""
    keep = TheirMessage(c, t, channel)
    try:
        yield keep
    except BaseException:
        keep.store(Frame.REAL)
        raise


def _react_alongside(
    c: Conversation, t: Turn, felt: tuple[ReactJudgement, str, str] | None
) -> Reaction | None:
    """A reaction to send with the reply, if the message calls for one. Logs the judgement."""
    if felt is None:
        return None
    judged, model, prompt = felt
    decision = decide_reaction(judged, c.store.turns_since_reaction(c.rel))
    decide(
        c,
        t,
        REACTED if decision.reaction is not None else "react: none",
        {
            "scorer": model,
            "prompt": REACT_PROMPT.ref,
            "inputs_hash": inputs_hash(prompt),
            "scores": {"tone": judged.tone, "confidence": judged.confidence},
        },
        reason=decision.reason,
    )
    return decision.reaction


def with_reaction(
    c: Conversation, t: Turn, felt: tuple[ReactJudgement, str, str] | None, sent: str
) -> str | ReactAndReply:
    reacted = _react_alongside(c, t, felt)
    mark(t, f"done: reply{' + ' + reacted.emoji if reacted else ''}, stored; handed to Telegram")
    return ReactAndReply(reacted, sent) if reacted is not None else sent


async def after_turn(c: Conversation, t: Turn, said: Utterance, sent: str | None) -> None:
    """Each feature's step once the turn is stored, in the registry's order."""
    for feature in FEATURES:
        if feature.after_turn is not None:
            await feature.after_turn(c, t, said, sent)
    await read_met(c, t, said, sent)


def log_frame(
    c: Conversation, t: Turn, outcome: tuple[Judgement, str, str] | None, stored: Frame
) -> None:
    """Record every frame judgement and what was stored, with the reason built by code."""
    judged = outcome[0] if outcome else None
    detail: dict[str, Json] = {"stored": stored.value}
    if outcome is not None:
        detail |= {
            "scorer": outcome[1],
            "prompt": FRAMES_PROMPT.ref,
            "schema_hash": frames_schema_hash(),
            "inputs_hash": frames_inputs_hash(outcome[2]),
            "scores": {"frame": outcome[0].frame.value, "confidence": outcome[0].confidence},
            "threshold": FRAME_MIN_CONFIDENCE,
        }
    decide(c, t, "frame", detail, reason=frame_reason(judged, stored))


def persist_reply(c: Conversation, t: Turn, reply: Reply, user_frame: Frame, channel: str) -> str:
    """Store the companion's reply and the decision that sent it. Returns what to send."""
    replied_at = t.now + timedelta(milliseconds=max(reply.latency_ms, 1))
    ids = (c.rel, t.session, t.turn)
    if not reply.text:
        decide(c, t, "model returned no text", kind=DecisionKind.DO_NOTHING, at=replied_at)
        return ""
    c.store.append_utterance(
        Utterance(
            UtteranceId(uuid.uuid4().hex),
            *ids,
            Speaker.COMPANION,
            reply.text,
            companion_frame(user_frame),
            channel,
            replied_at,
        )
    )
    decide(
        c,
        t,
        "replied",
        {
            "latency_ms": reply.latency_ms,
            "input_tokens": reply.input_tokens,
            "cache_read_tokens": reply.cache_read_tokens,
            "cache_write_tokens": reply.cache_write_tokens,
        },
        reason="replied: every user message gets a reply in v1",
        at=replied_at,
    )
    return reply.text


async def reaction_only(
    c: Conversation, t: Turn, keep: TheirMessage, in_scene: Frame, reaction: Reaction
) -> Reaction:
    """A turn answered by a reaction alone: their message is kept, and nothing else is stored."""
    said = keep.store(in_scene)
    await after_turn(c, t, said, None)
    mark(t, "done: reaction only")
    log.info("turn %s | ack -> %s\n  you: %s", t.turn[:8], reaction.emoji, t.text)
    return reaction


async def finish(
    c: Conversation, t: Turn, keep: TheirMessage, asm: Assembled, answered: Answered
) -> str | ReactAndReply:
    """The persist stage: their message kept with the frame the judge resolved, the request
    recorded for replay, the card logged, the reply stored, the notes' writes made, and what to
    send handed back."""
    reply, request = answered.reply, asm.request
    framed = answered.framed
    user_frame = frame_resolve(framed[0] if framed else None, fallback=answered.in_scene)
    said = keep.store(user_frame)
    if framed is not None:
        log_frame(c, t, framed, user_frame)
    c.store.record_turn(
        TurnRecord(
            t.turn,
            c.rel,
            t.session,
            request.prefix.sha256,
            "",
            request_sha256(request),
            reply.model,
            t.now,
            asm.card_text,
        )
    )
    CardLog(recorder(c, t), {b.id: why(b, asm.view_state) for b in asm.views}).write(asm.card)
    log.info(
        "turn %s | %s %dms in=%d cache_read=%d cache_write=%d%s\n  you: %s\n  it:  %s",
        t.turn[:8],
        reply.model,
        reply.latency_ms,
        reply.input_tokens,
        reply.cache_read_tokens,
        reply.cache_write_tokens,
        f" | frame={user_frame.value}" if user_frame is not Frame.REAL else "",
        t.text,
        reply.text or "(no reply)",
    )
    sent = persist_reply(c, t, reply, user_frame, keep.channel)
    for write in asm.after:  # what the notes used up, now that the turn is stored
        write()
    await after_turn(c, t, said, sent)
    return with_reaction(c, t, answered.felt, sent)
