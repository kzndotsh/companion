"""The talk and check stages of a turn: the talker and what runs beside it, then the checks a
reply passes before it is sent, and the floor's check on a held turn (ADR 0017)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from companion.core.floor import INTIMATE_CHECK
from companion.core.frames import (
    Judgement,
    needs_judge,
)
from companion.core.prompt.request import TalkerRequest
from companion.core.quip import PROMPT as QUIP_PROMPT
from companion.core.react import Judgement as ReactJudgement
from companion.core.recheck import DASHED as EM_DASH_CHECK
from companion.core.recheck import QUIP, code_checks
from companion.core.recheck import SERIOUS as RECHECK_SERIOUS
from companion.core.recheck import eligible as recheck_eligible
from companion.core.talker import Reply, Talker
from companion.core.types import (
    Frame,
    Json,
)
from companion.loops.turn import Answered, Heard, Routed, Turn, decide, mark, stop
from companion.turn.floor import judge_intimate
from companion.turn.frames import judge_frame
from companion.turn.quip import judge_quip
from companion.turn.react import judge_reaction

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.turn")


def start_beside(
    c: Conversation, t: Turn, request: TalkerRequest, talker: Talker
) -> tuple[
    asyncio.Future[Reply],
    asyncio.Future[tuple[Judgement, str, str] | None] | None,
    asyncio.Future[tuple[ReactJudgement, str, str] | None] | None,
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
    return talk, framing, asyncio.ensure_future(judge_reaction(c.judge, t.prior, t.text))


async def _redraw_empty(c: Conversation, t: Turn, request: TalkerRequest, talker: Talker) -> Reply:
    """An empty reply would be a silent turn (seen in 2 to 3% of long scene replies in tests): ask
    the same model once more, and send whatever comes back."""
    again = await talker.reply(request)
    _mark_reply(t, again)
    decide(c, t, "resampled", reason="resampled: the model returned no text")
    return again


async def _recheck(  # noqa: PLR0913, PLR0917
    c: Conversation,
    t: Turn,
    request: TalkerRequest,
    reply: Reply,
    heard: Heard | None,
    in_scene: Frame,
    talker: Talker,
) -> Reply:
    """The reply to send: the first, or one fresh draw when the first fails a check (two when the
    redraw still has an em dash: one redraw left 4 of 10 dashes in). On an ordinary
    turn every check runs and the result is logged; in a scene or on a serious turn only the code
    checks run, and only a resample is logged."""
    severity = heard[0].severity if heard is not None else None
    scene = talker is c.roleplay_talker or in_scene is not Frame.REAL
    code_only = scene or severity == RECHECK_SERIOUS
    if not c.resample:
        return reply
    if not reply.text.strip():
        return await _redraw_empty(c, t, request, talker)
    if not code_only and not recheck_eligible(severity=severity, in_scene=False, reply=reply.text):
        return reply
    failed = code_checks(reply.text, t.text, scene=scene)
    if code_only and not failed:
        return reply  # a scene or a serious turn gets only the code checks; a pass is not logged
    detail: dict[str, Json] = {}
    if not failed and c.judge is not None:
        judged = await judge_quip(c.judge, t.text, reply.text)
        if judged is not None:
            detail = {"scorer": judged[1], "prompt": QUIP_PROMPT.ref}
            if judged[0]:
                failed.append(QUIP)
    mark(t, f"recheck: {', '.join(failed) or 'passed'}")
    again = None
    if failed:
        again = await talker.reply(request)
        _mark_reply(t, again)
        detail |= {"discarded": reply.text, "checks": list[Json](failed)}
        still = [x for x in code_checks(again.text, t.text, scene=scene) if x == EM_DASH_CHECK]
        if still and again.text:  # the model that dashes once often dashes again: one more draw
            detail |= {"discarded_again": again.text}
            third = await talker.reply(request)
            _mark_reply(t, third)
            again = third if third.text else again
    reason = f"resampled: {', '.join(failed)}" if failed else "kept: the reply passed its checks"
    decide(c, t, "recheck", detail or None, reason=reason)
    return again if again is not None and again.text else reply


async def checked(  # noqa: PLR0913, PLR0917
    c: Conversation,
    t: Turn,
    request: TalkerRequest,
    reply: Reply,
    heard: Heard | None,
    in_scene: Frame,
    talker: Talker,
    *,
    held: bool,
) -> Reply:
    """The reply after its checks: the habit checks on an ordinary turn, the floor's on a held
    one."""
    reply = await _recheck(c, t, request, reply, heard, in_scene, talker)
    return await _hold_check(c, t, request, reply, talker) if held else reply


async def _hold_check(
    c: Conversation, t: Turn, request: TalkerRequest, reply: Reply, talker: Talker
) -> Reply:
    """On a turn the floor held, the reply must not be intimate (ADR 0017). An intimate or unread
    reply is drawn again with the same request, then once more with only their last message in
    view, so the history that pulled it along is gone. If all three read as intimate, nothing is
    sent this turn. Every step is logged with what was discarded; no reply is written by code."""
    if c.judge is None:
        return reply
    lean = TalkerRequest(prefix=request.prefix, messages=request.messages[-1:], card=request.card)
    tries = (request, lean)
    discarded: list[Json] = []
    for attempt in range(len(tries) + 1):
        if await judge_intimate(c.judge, reply.text) is False:
            break
        discarded.append(reply.text)
        if attempt < len(tries):
            reply = await talker.reply(tries[attempt])
            _mark_reply(t, reply)
    else:
        reply = Reply(text="", model=reply.model, latency_ms=reply.latency_ms)
    if discarded:
        sent = ["a second reply", "a reply drawn with only their last message", "nothing"]
        decide(
            c,
            t,
            "floor: held reply",
            {"discarded": discarded, "prompt": INTIMATE_CHECK.ref},
            reason="floor: a reply on a held turn read as intimate,"
            f" sent {sent[len(discarded) - 1]}",
        )
    return reply


async def await_beside(
    t: Turn,
    talk: asyncio.Future[Reply],
    framing: asyncio.Future[Any] | None,
    feeling: asyncio.Future[Any] | None,
) -> tuple[Reply, Any, Any]:
    """The reply, then the frame and reaction judgements that ran beside it, marking each."""
    reply = await talk
    _mark_reply(t, reply)
    outcome = await framing if framing is not None else None
    if framing is not None:
        mark(t, "frame judge done")
    felt = await feeling if feeling is not None else None
    if feeling is not None:
        mark(t, "reaction judge done")
    return reply, outcome, felt


def _mark_reply(t: Turn, reply: Reply) -> None:
    mark(
        t,
        f"talker done: {reply.model} {reply.latency_ms}ms in={reply.input_tokens}"
        f" cache_read={reply.cache_read_tokens} cost=${reply.cost_usd:.5f},"
        f" {len(reply.text.split())} words",
    )


async def talk(c: Conversation, t: Turn, request: TalkerRequest, routed: Routed) -> Answered:
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
        )
    except BaseException:
        await stop(running, framing, feeling)
        raise
    return Answered(reply, framed, felt, routed.in_scene)
