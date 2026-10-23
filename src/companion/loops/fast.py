"""The fast loop: one user message in, one reply out, everything logged with a reason."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from companion.core.ack import PROMPT as ACK_PROMPT
from companion.core.ack import (
    REACT_THRESHOLD,
    ReactAndReply,
    Reaction,
    inputs_hash,
    is_candidate,
    reaction_for,
    render_reason,
    schema_hash,
)
from companion.core.basics import NAME_CAPTURE, asked_for_name, knows_name, name_belief
from companion.core.clock import utc_now
from companion.core.extractor import Extractor
from companion.core.frames import (
    MIN_CONFIDENCE as FRAME_MIN_CONFIDENCE,
)
from companion.core.frames import PROMPT as FRAMES_PROMPT
from companion.core.frames import (
    Judgement,
    companion_frame,
    scene_frame,
)
from companion.core.frames import render_reason as frame_reason
from companion.core.frames import resolve as frame_resolve
from companion.core.history import HISTORY_LIMIT
from companion.core.listening import SERIOUS
from companion.core.moves import PROMPT as HABITS_PROMPT
from companion.core.moves import replies_to_read
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import request_sha256
from companion.core.react import PROMPT as REACT_PROMPT
from companion.core.react import Judgement as ReactJudgement
from companion.core.react import decide as decide_reaction
from companion.core.relevance import Embedder
from companion.core.replay import TurnRecord
from companion.core.talker import Reply, Talker
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.core.views import why
from companion.loops.ack import judge
from companion.loops.assemble import CardLog, assemble
from companion.loops.basics import judge_name
from companion.loops.beside import shadows
from companion.loops.frames import inputs_hash as frames_inputs_hash
from companion.loops.frames import schema_hash as frames_schema_hash
from companion.loops.listen import judge_listening
from companion.loops.moves import HabitMemory, find_habits
from companion.loops.notes import look
from companion.loops.persist import TheirMessage, store_user, their_message
from companion.loops.record import Recorder
from companion.loops.route import route_turn
from companion.loops.spendcap import NOTICE, first_notice_today, over_cap
from companion.loops.talk import await_beside, checked, start_beside
from companion.loops.turn import Heard, Turn, decide, mark, recorder
from companion.store.sqlite.decisions import REACTED
from companion.store.sqlite.store import Store

log = logging.getLogger("companion.turn")


def _id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True, slots=True)
class Conversation:
    store: Store
    talker: Talker
    prefix: Prefix
    rel: RelationshipId
    judge: Extractor | None = None
    habits: HabitMemory = field(default_factory=HabitMemory)
    roleplay_talker: Talker | None = None  # replies while a pretend scene is in progress
    daily_cap_usd: float | None = None  # nothing paid runs once today's spend reaches this
    listen: bool = True  # ask how serious a message is before the reply
    mood: str = "off"  # off, shadow (worked out and logged, never shown) or on (ADR 0016)
    resample: bool = False  # draw one fresh reply when the first fails a check (core/recheck.py)
    route_intimate: bool = False  # intimate talk may go to the roleplay talker (ADR 0017)
    roleplay_prefix: Prefix | None = (
        None  # the roleplay talker's system prompt, with the sheet's scene section
    )
    embedder: Embedder | None = None  # the relevance look-up runs in shadow when set
    embed_model: str = ""
    lore: str = "off"  # on, shadow or off: its tastes nearest their message (ADR 0020)
    scene_reminder: str = ""  # the character's scene reminder, sent after the history in scenes
    relevance: str = "shadow"  # on (picks shown when a memory is near), shadow or off (ADR 0018)
    reminders: bool = True  # reminders they ask for are read and set (J50)
    episodes: str = "off"  # what they did together lately, when it bears: on, shadow or off (J12)

    async def handle(
        self, session: SessionId, text: str, channel: str, now: datetime | None = None
    ) -> str | Reaction | ReactAndReply:
        now = now or utc_now()
        capped = _stopped_by_cap(self, session, text, channel, now)
        if capped is not None:
            return capped
        return await _handle_turn(self, session, text, channel, now)


async def _ack_reaction(c: Conversation, t: Turn) -> Reaction | None:
    """A reaction if this short message only acknowledges. Logs every judgement it makes."""
    if c.judge is None or not is_candidate(t.text, t.prior, after_serious=_after_serious(c, t)):
        mark(t, "ack judge skipped: not a candidate for a reaction")
        return None
    outcome = await judge(c.judge, t.prior, t.text)
    if outcome is None:
        mark(t, "ack judge gave no answer; replying")
        return None
    judged, model, prompt = outcome
    reaction = reaction_for(judged)
    mark(
        t, f"ack judged {judged.kind} {judged.confidence:.2f} -> {'react' if reaction else 'reply'}"
    )
    decide(
        c,
        t,
        REACTED if reaction is not None else "ack: replied",
        {
            "scorer": model,
            "prompt": ACK_PROMPT.ref,
            "schema_hash": schema_hash(),
            "inputs_hash": inputs_hash(prompt),
            "scores": {"kind": judged.kind, "confidence": judged.confidence},
            "threshold": REACT_THRESHOLD,
        },
        reason=render_reason(judged, reaction is not None),
    )
    return reaction


def _after_serious(c: Conversation, t: Turn) -> bool:
    """Whether the listening judge found their previous message serious (severity 2 or more)."""
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs:
        return False
    for d in c.store.decisions_for_turn(c.rel, theirs[-1].turn_id):
        labels = d.detail.get("labels") if d.detail else None
        severity = labels.get("severity") if isinstance(labels, dict) else None
        if isinstance(severity, int) and not isinstance(severity, bool) and severity >= SERIOUS:
            return True
    return False


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


def _stopped_by_cap(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime
) -> str | None:
    """At the daily cap the user's message is kept and nothing paid runs, and they are told once.

    None means under the cap and the turn goes ahead. An empty string means send nothing."""
    spent = over_cap(c.store, c.rel, c.daily_cap_usd, now)
    if spent is None:
        return None
    turn = TurnId(_id())
    t = Turn(session, turn, now, [], text)
    store_user(c, t, channel, Frame.REAL)
    Recorder(c.store, c.rel, session, turn, TraceId(turn), now).decide(
        "daily spend cap reached",
        reason=f"daily spend cap reached: ${spent:.2f} of ${c.daily_cap_usd or 0:.2f}, no reply",
    )
    return NOTICE if first_notice_today(c.store, c.rel, now) else ""


def _with_reaction(
    c: Conversation, t: Turn, felt: tuple[ReactJudgement, str, str] | None, sent: str
) -> str | ReactAndReply:
    reacted = _react_alongside(c, t, felt)
    mark(t, f"done: reply{' + ' + reacted.emoji if reacted else ''}, stored; handed to Telegram")
    return ReactAndReply(reacted, sent) if reacted is not None else sent


async def _capture_name(c: Conversation, t: Turn, said: Utterance) -> None:
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
        c.store.insert_belief(name_belief(said, name, _id(), t.now))
        reason = f"basics: remembered what to call them ({name})"
    decide(c, t, "basics: name capture", {"prompt": NAME_CAPTURE.ref}, reason=reason)


async def _stop(*tasks: asyncio.Future[Any] | None) -> None:
    """Cancel whatever is still running beside the reply."""
    for task in tasks:
        if task is None:
            continue
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task


def _log_frame(
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


def _persist_reply(c: Conversation, t: Turn, reply: Reply, user_frame: Frame, channel: str) -> str:
    """Store the companion's reply and the decision that sent it. Returns what to send."""
    replied_at = t.now + timedelta(milliseconds=max(reply.latency_ms, 1))
    ids = (c.rel, t.session, t.turn)
    if not reply.text:
        decide(c, t, "model returned no text", kind=DecisionKind.DO_NOTHING, at=replied_at)
        return ""
    c.store.append_utterance(
        Utterance(
            UtteranceId(_id()),
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


async def _listening(c: Conversation, t: Turn, in_scene: Frame) -> Heard | None:
    """How serious the message is and what they are doing. Not asked in a scene."""
    if c.judge is None or not c.listen or in_scene is not Frame.REAL:
        return None
    return await judge_listening(c.judge, t.prior, t.text)


async def _handle_turn(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime | None
) -> str | Reaction | ReactAndReply:
    store, rel = c.store, c.rel
    now = now or utc_now()
    turn = TurnId(_id())
    prior = store.history_before(rel, now, HISTORY_LIMIT)
    t = Turn(session, turn, now, prior, text)
    in_scene = scene_frame(prior, now)
    async with their_message(c, t, channel) as keep:
        return await _turn(c, t, keep, in_scene, channel)


async def _turn(
    c: Conversation, t: Turn, keep: TheirMessage, in_scene: Frame, channel: str
) -> str | Reaction | ReactAndReply:
    """The stages of one turn, inside the guard that keeps their message."""
    store, rel, turn, now, text = c.store, c.rel, t.turn, t.now, t.text
    listening = asyncio.ensure_future(_listening(c, t, in_scene))
    heard: Heard | None = None
    try:
        reaction = await _ack_reaction(c, t)
        if reaction is None:
            heard = await listening
    except BaseException:
        await _stop(listening)
        raise
    if reaction is not None:
        await _stop(listening)
        said = keep.store(in_scene)
        await _capture_name(c, t, said)
        mark(t, "done: reaction only")
        log.info("turn %s | ack -> %s\n  you: %s", turn[:8], reaction.emoji, text)
        return reaction
    talker, held, read, brushed = await route_turn(c, t, in_scene, heard)
    looked = await look(c, t, in_scene, heard, read)
    asm = assemble(
        c,
        t,
        in_scene,
        heard,
        looked,
        held=held,
        brushed=brushed,
        roleplay=talker is c.roleplay_talker,
    )
    request, card_text, card, views, view_state = (
        asm.request,
        asm.card_text,
        asm.card,
        asm.views,
        asm.view_state,
    )
    shadows(c, t, in_scene, heard, card)
    talk, framing, feeling = start_beside(c, t, request, talker)
    try:
        reply, outcome, felt = await await_beside(t, talk, framing, feeling)
        reply = await checked(c, t, request, reply, heard, in_scene, talker, held=held)
    except BaseException:
        await _stop(talk, framing, feeling)
        raise
    user_frame = frame_resolve(outcome[0] if outcome else None, fallback=in_scene)
    said = keep.store(user_frame)
    if framing is not None:
        _log_frame(c, t, outcome, user_frame)
    store.record_turn(
        TurnRecord(
            turn,
            rel,
            t.session,
            request.prefix.sha256,
            "",
            request_sha256(request),
            reply.model,
            now,
            card_text,
        )
    )
    CardLog(recorder(c, t), {b.id: why(b, view_state) for b in views}).write(card)
    log.info(
        "turn %s | %s %dms in=%d cache_read=%d cache_write=%d%s\n  you: %s\n  it:  %s",
        turn[:8],
        reply.model,
        reply.latency_ms,
        reply.input_tokens,
        reply.cache_read_tokens,
        reply.cache_write_tokens,
        f" | frame={user_frame.value}" if user_frame is not Frame.REAL else "",
        text,
        reply.text or "(no reply)",
    )
    sent = _persist_reply(c, t, reply, user_frame, channel)
    for write in asm.after:  # what the notes used up, now that the turn is stored
        write()
    await _capture_name(c, t, said)
    return _with_reaction(c, t, felt, sent)
