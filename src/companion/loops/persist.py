"""Their message for a turn, stored in exactly one place (the persist stage of a turn)."""

from __future__ import annotations

import contextlib
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import TYPE_CHECKING

from companion.core.ack import (
    ReactAndReply,
    Reaction,
    inputs_hash,
)
from companion.core.basics import NAME_CAPTURE, asked_for_name, knows_name, name_belief
from companion.core.frames import (
    MIN_CONFIDENCE as FRAME_MIN_CONFIDENCE,
)
from companion.core.frames import PROMPT as FRAMES_PROMPT
from companion.core.frames import (
    Judgement,
    companion_frame,
)
from companion.core.frames import render_reason as frame_reason
from companion.core.moves import PROMPT as HABITS_PROMPT
from companion.core.moves import replies_to_read
from companion.core.react import PROMPT as REACT_PROMPT
from companion.core.react import Judgement as ReactJudgement
from companion.core.react import decide as decide_reaction
from companion.core.talker import Reply
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    Speaker,
    Utterance,
    UtteranceId,
)
from companion.loops.basics import judge_name
from companion.loops.frames import inputs_hash as frames_inputs_hash
from companion.loops.frames import schema_hash as frames_schema_hash
from companion.loops.moves import find_habits
from companion.loops.turn import Turn, decide, mark
from companion.store.sqlite.decisions import REACTED

if TYPE_CHECKING:
    from companion.loops.fast import Conversation

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


def _check_habits(c: Conversation, t: Turn, sent: str) -> None:
    """After the reply is out, read the last few replies in the background for habits."""
    if c.judge is None:
        return
    replies = replies_to_read(t.prior, sent)
    if not replies:
        return

    async def look() -> list[str] | None:
        found = await find_habits(c.judge, replies)  # type: ignore[arg-type]
        if found is None:
            return None
        habits, model, prompt = found
        detail: dict[str, Json] = {
            "scorer": model,
            "prompt": HABITS_PROMPT.ref,
            "inputs_hash": inputs_hash(prompt),
            "habits": list[Json](habits),
        }
        decide(
            c,
            t,
            "habit check",
            detail,
            reason=f"habit check: {len(habits)} habits found in the last {len(replies)} replies",
        )
        return habits

    c.habits.start(look())


def with_reaction(
    c: Conversation, t: Turn, felt: tuple[ReactJudgement, str, str] | None, sent: str
) -> str | ReactAndReply:
    reacted = _react_alongside(c, t, felt)
    mark(t, f"done: reply{' + ' + reacted.emoji if reacted else ''}, stored; handed to Telegram")
    return ReactAndReply(reacted, sent) if reacted is not None else sent


async def capture_name(c: Conversation, t: Turn, said: Utterance) -> None:
    """When its last message asked what to call them, read their answer and remember the name,
    quoting their own words. Logged either way."""
    asked = next((u.text for u in reversed(t.prior) if u.speaker is Speaker.COMPANION), "")
    if c.judge is None or not asked_for_name(asked):
        return
    if knows_name(c.store.user_beliefs(c.rel)):
        return
    name = await judge_name(c.judge, asked, t.text)
    reason = "basics: no name in their answer"
    if name is not None:
        c.store.insert_belief(name_belief(said, name, uuid.uuid4().hex, t.now))
        reason = f"basics: remembered what to call them ({name})"
    decide(c, t, "basics: name capture", {"prompt": NAME_CAPTURE.ref}, reason=reason)


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
    _check_habits(c, t, reply.text)
    return reply.text
