"""The talk stage of a turn: the talker and what runs beside it, then the reply gate
(`turn/gate.py`) on what it wrote."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from companion.core.frames import (
    Judgement,
    needs_judge,
)
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply, Talker
from companion.core.turn.reactions import ToneRead
from companion.kit.current import Turn, mark
from companion.turn.frames import judge_frame
from companion.turn.gate import checked, mark_reply
from companion.turn.reactions import judge_alongside
from companion.turn.values import Answered, Routed, stop

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.turn")


def start_beside(
    c: Runtime, t: Turn, request: TalkerRequest, talker: Talker
) -> tuple[
    asyncio.Future[Reply],
    asyncio.Future[tuple[Judgement, str, str] | None] | None,
    asyncio.Future[tuple[ToneRead, str, str] | None] | None,
]:
    """Start the reply, and beside it the frame judge and the reaction judge, so neither adds a
    wait. A confident acknowledgement cancels all of them."""
    talk = asyncio.ensure_future(talker.reply(request))
    if c.judge is None:
        return talk, None, None
    framing = (
        asyncio.ensure_future(judge_frame(c.judge, t.prior, t.text))
        if needs_judge(t.text, t.prior, t.now)
        else None
    )
    return talk, framing, asyncio.ensure_future(judge_alongside(c.judge, t.prior, t.text))


async def await_beside(
    t: Turn,
    talk: asyncio.Future[Reply],
    framing: asyncio.Future[Any] | None,
    feeling: asyncio.Future[Any] | None,
) -> tuple[Reply, Any, Any]:
    """The reply, then the frame and reaction judgements that ran beside it, marking each."""
    reply = await talk
    mark_reply(t, reply)
    outcome = await framing if framing is not None else None
    if framing is not None:
        mark(t, "frame judge done")
    felt = await feeling if feeling is not None else None
    if feeling is not None:
        mark(t, "reaction judge done")
    return reply, outcome, felt


async def talk(c: Runtime, t: Turn, request: TalkerRequest, routed: Routed) -> Answered:
    """The talk and check stages: the talker, with the frame and reaction judges beside it, then
    the checks the reply passes before it is sent. A failure stops all three and goes on up."""
    running, framing, feeling = start_beside(c, t, request, routed.talker)
    try:
        reply, framed, felt = await await_beside(t, running, framing, feeling)
        reply = await checked(
            c,
            t,
            request,
            reply,
            routed.heard,
            routed.in_scene,
            routed.talker,
            held=routed.held,
            crisis=routed.crisis,
        )
    except BaseException:
        await stop(running, framing, feeling)
        raise
    return Answered(reply, framed, felt, routed.in_scene)
