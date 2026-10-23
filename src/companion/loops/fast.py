"""The fast loop: one user message in, one reply out, everything logged with a reason."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
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
from companion.core.clock import utc_now
from companion.core.extractor import Extractor
from companion.core.frames import resolve as frame_resolve
from companion.core.frames import (
    scene_frame,
)
from companion.core.history import HISTORY_LIMIT
from companion.core.listening import SERIOUS
from companion.core.prompt.prefix import Prefix
from companion.core.prompt.request import request_sha256
from companion.core.relevance import Embedder
from companion.core.replay import TurnRecord
from companion.core.talker import Talker
from companion.core.types import (
    Frame,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
)
from companion.core.views import why
from companion.loops.ack import judge
from companion.loops.assemble import CardLog, assemble
from companion.loops.beside import shadows
from companion.loops.listen import judge_listening
from companion.loops.moves import HabitMemory
from companion.loops.notes import look
from companion.loops.persist import (
    TheirMessage,
    capture_name,
    log_frame,
    persist_reply,
    store_user,
    their_message,
    with_reaction,
)
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


async def _stop(*tasks: asyncio.Future[Any] | None) -> None:
    """Cancel whatever is still running beside the reply."""
    for task in tasks:
        if task is None:
            continue
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task


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
        await capture_name(c, t, said)
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
        log_frame(c, t, outcome, user_frame)
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
    sent = persist_reply(c, t, reply, user_frame, channel)
    for write in asm.after:  # what the notes used up, now that the turn is stored
        write()
    await capture_name(c, t, said)
    return with_reaction(c, t, felt, sent)
