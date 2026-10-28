"""The reply path: one user message in, one reply out, everything logged with a reason."""

from __future__ import annotations

import logging
import uuid
from dataclasses import replace
from datetime import datetime

from companion.core.clock import utc_now
from companion.core.frames import (
    scene_frame,
)
from companion.core.history import HISTORY_LIMIT
from companion.core.turn.ack import (
    ReactAndReply,
    Reaction,
    ThenSend,
)
from companion.core.turn.quoted import Quoted
from companion.core.types import (
    Frame,
    SessionId,
    TraceId,
    TurnId,
)
from companion.kit.current import Turn
from companion.kit.record import Recorder
from companion.kit.runtime import Runtime
from companion.kit.spendcap import NOTICE, first_notice_today, over_cap
from companion.turn.assemble import assemble
from companion.turn.beside import shadows
from companion.turn.crisis import off_scene, reading_of, then_line
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


async def handle(  # noqa: PLR0913
    c: Runtime,
    session: SessionId,
    text: str,
    channel: str,
    now: datetime | None = None,
    *,
    quoted: Quoted | None = None,
    message_id: str | None = None,
) -> str | Reaction | ReactAndReply | ThenSend:
    """One message in, one reply out (or a reaction, or nothing at the cap). `quoted` is the
    message they used reply on, if they did; `message_id` their message's id on the surface."""
    now = now or utc_now()
    t = Turn(session, TurnId(_id()), now, [], text, quoted, message_id)
    capped = _stopped_by_cap(c, t, channel)
    if capped is not None:
        return capped
    prior = c.store.history_before(c.rel, now, HISTORY_LIMIT)
    return await _handle_turn(c, replace(t, prior=prior), channel)


def _stopped_by_cap(c: Runtime, t: Turn, channel: str) -> str | None:
    """At the daily cap the user's message is kept and nothing paid runs, and they are told once.

    None means under the cap and the turn goes ahead. An empty string means send nothing."""
    spent = over_cap(c.store, c.rel, c.daily_cap_usd, t.now)
    if spent is None:
        return None
    store_user(c, t, channel, Frame.REAL)
    Recorder(c.store, c.rel, t.session, t.turn, TraceId(t.turn), t.now).decide(
        "daily spend cap reached",
        reason=f"daily spend cap reached: ${spent:.2f} of ${c.daily_cap_usd or 0:.2f}, no reply",
    )
    return NOTICE if first_notice_today(c.store, c.rel, t.now) else ""


async def _handle_turn(
    c: Runtime, t: Turn, channel: str
) -> str | Reaction | ReactAndReply | ThenSend:
    in_scene = scene_frame(t.prior, t.now)
    async with their_message(c, t, channel) as keep:
        return await _turn(c, t, keep, in_scene)


async def _turn(
    c: Runtime, t: Turn, keep: TheirMessage, in_scene: Frame
) -> str | Reaction | ReactAndReply | ThenSend:
    """The stages of one turn, inside the guard that keeps their message."""
    listened = await listen(c, t, in_scene)
    if listened.reaction is not None:
        return await reaction_only(c, t, keep, in_scene, listened.reaction)
    heard = listened.heard
    routed = await route_turn(c, t, in_scene, heard)
    looked = await look(c, t, in_scene, heard, routed.read)
    reading = reading_of(looked)
    routed = off_scene(c, t, routed, reading)
    asm = assemble(
        c,
        t,
        routed.in_scene,
        heard,
        looked,
        held=routed.held,
        brushed=routed.brushed,
        roleplay=routed.talker is c.roleplay_talker,
        risk=reading is not None and reading.acts and reading.risk,
    )
    shadows(c, t, routed.in_scene, heard, asm.card)
    answered = await talk(c, t, asm.request, routed)
    out = await finish(c, t, keep, asm, answered)
    return then_line(keep, reading, out, answered.reply)
