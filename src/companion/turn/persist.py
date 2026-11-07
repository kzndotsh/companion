"""Their message for a turn, stored in exactly one place (the persist stage of a turn)."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import TYPE_CHECKING

from companion.core.frames import (
    MIN_CONFIDENCE as FRAME_MIN_CONFIDENCE,
)
from companion.core.frames import PROMPT as FRAMES_PROMPT
from companion.core.frames import SCHEMA as FRAMES_SCHEMA
from companion.core.frames import (
    Judgement,
    companion_frame,
)
from companion.core.frames import render_reason as frame_reason
from companion.core.frames import resolve as frame_resolve
from companion.core.ids import new_id
from companion.core.prompt.request import request_sha256
from companion.core.replay import TurnRecord
from companion.core.talker import Reply
from companion.core.turn.context import Scored
from companion.core.turn.reactions import ToneRead
from companion.core.turn.reply import ReactAndReply, Reaction
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    Speaker,
    Utterance,
    UtteranceId,
)
from companion.kit.beside import beside
from companion.kit.current import Turn, decide, mark
from companion.kit.features import Moment
from companion.registry import FEATURES
from companion.turn.assemble import Assembled
from companion.turn.reactions import react_alongside
from companion.turn.values import Answered

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.turn")


def store_user(c: Runtime, t: Turn, platform: str, frame: Frame) -> Utterance:
    said = Utterance(
        UtteranceId(new_id()),
        c.rel,
        t.turn,
        Speaker.USER,
        t.text,
        frame,
        platform,
        t.now,
    )
    c.store.append_utterance(said)
    if t.message_id is not None:
        c.store.record_message(c.rel, platform, t.message_id, t.turn, t.now, sent=False)
    return said


class TheirMessage:
    """Their message for this turn, stored exactly once: with the frame the turn resolved, or, if
    the turn fails before that, as real when the guard closes."""

    def __init__(self, c: Runtime, t: Turn, platform: str) -> None:
        self.c, self.t, self.platform = c, t, platform
        self.said: Utterance | None = None

    def store(self, frame: Frame) -> Utterance:
        if self.said is None:
            self.said = store_user(self.c, self.t, self.platform, frame)
        return self.said


@contextlib.asynccontextmanager
async def their_message(c: Runtime, t: Turn, platform: str) -> AsyncGenerator[TheirMessage]:
    """The one place their message is stored. A turn that fails at any stage still keeps it, as
    real, and the failure goes on up; before, an error in the look-ups or the card lost it."""
    keep = TheirMessage(c, t, platform)
    try:
        yield keep
    except BaseException:
        keep.store(Frame.REAL)
        raise


def with_reaction(
    c: Runtime, t: Turn, felt: Scored[ToneRead] | None, sent: str
) -> str | ReactAndReply:
    reacted = react_alongside(c, t, felt)
    mark(t, f"done: reply{' + ' + reacted.emoji if reacted else ''}, stored; handed to the chat")
    return ReactAndReply(reacted, sent) if reacted is not None else sent


async def after_turn(m: Moment, said: Utterance, sent: str | None) -> None:
    """Each feature's step once the turn is stored, in the registry's order. One that must finish
    first (`Feature.must_finish`) is waited for; the rest run beside the reply, a failure logged."""
    for feature in FEATURES:
        if feature.after_turn is None or not feature.can_read(m.c):
            continue
        step = feature.after_turn(m, said, sent)
        if feature.must_finish:
            await step
        else:
            beside(step)


def log_frame(c: Runtime, t: Turn, outcome: Scored[Judgement] | None, stored: Frame) -> None:
    """Record every frame judgement and what was stored, with the reason built by code."""
    judged = outcome.read if outcome else None
    detail: dict[str, Json] = {"stored": stored.value}
    if outcome is not None and judged is not None:
        detail |= outcome.detail(
            FRAMES_PROMPT.ref,
            schema=FRAMES_SCHEMA,
            scores={"frame": judged.frame.value, "confidence": judged.confidence},
            threshold=FRAME_MIN_CONFIDENCE,
        )
    decide(c, t, "frame", detail, reason=frame_reason(judged, stored))


def persist_reply(c: Runtime, t: Turn, reply: Reply, user_frame: Frame, platform: str) -> str:
    """Store the companion's reply and the decision that sent it. Returns what to send."""
    replied_at = t.now + timedelta(milliseconds=max(reply.latency_ms, 1))
    ids = (c.rel, t.turn)
    if not reply.text:
        decide(c, t, "model returned no text", kind=DecisionKind.DO_NOTHING, at=replied_at)
        return ""
    c.store.append_utterance(
        Utterance(
            UtteranceId(new_id()),
            *ids,
            Speaker.COMPANION,
            reply.text,
            companion_frame(user_frame),
            platform,
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


async def reaction_only(m: Moment, keep: TheirMessage, reaction: Reaction) -> Reaction:
    """A turn answered by a reaction alone: their message is kept, and nothing else is stored."""
    t = m.t
    said = keep.store(m.in_scene)
    await after_turn(m, said, None)
    mark(t, "done: reaction only")
    log.info("turn %s | ack -> %s\n  you: %s", t.turn[:8], reaction.emoji, t.text)
    return reaction


async def finish(
    c: Runtime, t: Turn, keep: TheirMessage, asm: Assembled, answered: Answered
) -> str | ReactAndReply:
    """The persist stage: their message kept with the frame the judge resolved, the request
    recorded for replay, the card logged, the reply stored, the notes' writes made, and what to
    send handed back."""
    reply, request = answered.reply, asm.request
    framed = answered.framed
    user_frame = frame_resolve(framed.read if framed else None, fallback=answered.in_scene)
    said = keep.store(user_frame)
    if framed is not None:
        log_frame(c, t, framed, user_frame)
    c.store.record_turn(
        TurnRecord(
            t.turn,
            c.rel,
            request.prefix.sha256,
            "",
            request_sha256(request),
            reply.model,
            t.now,
            asm.card_text,
        )
    )
    asm.cards.write(asm.card)
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
    sent = persist_reply(c, t, reply, user_frame, keep.platform)
    if sent:  # what the notes used up, now that a reply is stored; an empty one uses none
        for write in asm.after:
            write()
    await after_turn(asm.moment, said, sent)
    return with_reaction(c, t, answered.felt, sent)
