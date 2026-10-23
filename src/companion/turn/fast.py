"""The fast loop: one user message in, one reply out, everything logged with a reason."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from companion.core.ack import (
    ReactAndReply,
    Reaction,
)
from companion.core.clock import utc_now
from companion.core.frames import (
    scene_frame,
)
from companion.core.history import HISTORY_LIMIT
from companion.core.types import (
    Frame,
    SessionId,
    TraceId,
    TurnId,
)
from companion.loops.conversation import Conversation
from companion.loops.record import Recorder
from companion.loops.spendcap import NOTICE, first_notice_today, over_cap
from companion.loops.turn import Turn
from companion.turn.assemble import assemble
from companion.turn.beside import shadows
from companion.turn.hear import listen
from companion.turn.notes import look
from companion.turn.persist import (
    TheirMessage,
    finish,
    reaction_only,
    store_user,
    their_message,
)
from companion.turn.route import route_turn
from companion.turn.talk import talk

log = logging.getLogger("companion.turn")


def _id() -> str:
    return uuid.uuid4().hex


async def handle(
    c: Conversation, session: SessionId, text: str, channel: str, now: datetime | None = None
) -> str | Reaction | ReactAndReply:
    """One message in, one reply out (or a reaction, or nothing at the cap)."""
    now = now or utc_now()
    capped = _stopped_by_cap(c, session, text, channel, now)
    if capped is not None:
        return capped
    return await _handle_turn(c, session, text, channel, now)


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
        return await _turn(c, t, keep, in_scene)


async def _turn(
    c: Conversation, t: Turn, keep: TheirMessage, in_scene: Frame
) -> str | Reaction | ReactAndReply:
    """The stages of one turn, inside the guard that keeps their message."""
    listened = await listen(c, t, in_scene)
    if listened.reaction is not None:
        return await reaction_only(c, t, keep, in_scene, listened.reaction)
    heard = listened.heard
    routed = await route_turn(c, t, in_scene, heard)
    looked = await look(c, t, in_scene, heard, routed.read)
    asm = assemble(
        c,
        t,
        in_scene,
        heard,
        looked,
        held=routed.held,
        brushed=routed.brushed,
        roleplay=routed.talker is c.roleplay_talker,
    )
    shadows(c, t, in_scene, heard, asm.card)
    answered = await talk(c, t, asm.request, routed)
    return await finish(c, t, keep, asm, answered)
