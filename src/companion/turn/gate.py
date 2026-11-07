"""The reply gate's sequence: the checks a reply passes before it is sent, in order, with their
effects (ADR 0017, 0022). What each check is lives in `core/reply_gate.py`.

The order, as `checked` runs it: an empty reply is drawn once more; the code checks, then the quip
judge; the crisis path's method check; then on a turn the floor held, the intimate check and the
check for a reply that announces the hold. A check that fails draws the reply again with the same
model and logs it with what was discarded. Nothing is edited; no reply is written by code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from companion.core import switch
from companion.core.extractor import StructuredModel
from companion.core.prompt.request import TalkerRequest
from companion.core.reply_gate import (
    DASHED,
    GENERIC,
    QUIP,
    QUIP_PROMPT,
    QUIP_SCHEMA,
    RECHECK,
    RESAMPLED,
    QuipVerdict,
    announces_limit,
    code_checks,
    eligible,
    parse_quip,
    quip_prompt,
)
from companion.core.talker import Reply, Talker
from companion.core.turn.floor import INTIMATE_CHECK
from companion.core.types import Json
from companion.kit.ask import Judge, ask
from companion.kit.current import Turn, decide, mark
from companion.turn.crisis import method_checked
from companion.turn.floor import judge_intimate
from companion.turn.values import Routed, moment_of

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

QUIP_TIMEOUT_SECONDS = 2.5

QUIP_JUDGE = Judge(
    "quip",
    QUIP_PROMPT,
    QUIP_SCHEMA,
    parse_quip,
    timeout=QUIP_TIMEOUT_SECONDS,
    unread="the reply is kept",
)


async def judge_quip(
    extractor: StructuredModel, their_text: str, reply: str
) -> tuple[QuipVerdict, str, str, float] | None:
    """Whether it added a joke or a generic reaction, the model id, the prompt and the cost, or
    None if it could not be read in time."""
    prompt = quip_prompt(their_text, reply)
    got = await ask(extractor, QUIP_JUDGE, prompt)
    return None if got is None else (got.value, got.model, prompt, got.cost_usd)


def mark_reply(t: Turn, reply: Reply) -> None:
    mark(
        t,
        f"talker done: {reply.model} {reply.latency_ms}ms in={reply.input_tokens}"
        f" cache_read={reply.cache_read_tokens} cost=${reply.cost_usd:.5f},"
        f" {len(reply.text.split())} words",
    )


async def _redraw_empty(c: Runtime, t: Turn, request: TalkerRequest, talker: Talker) -> Reply:
    """An empty reply would be a silent turn (seen in 2 to 3% of long scene replies in tests): ask
    the same model once more, and send whatever comes back."""
    again = await talker.reply(request)
    mark_reply(t, again)
    decide(c, t, RESAMPLED, reason="resampled: the model returned no text")
    return again


async def _habit_checks(
    c: Runtime, t: Turn, request: TalkerRequest, reply: Reply, routed: Routed
) -> Reply:
    """The reply to send: the first, or one fresh draw when the first fails a check (two when the
    redraw still has an em dash: one redraw left 4 of 10 dashes in). On an ordinary
    turn every check runs and the result is logged; in a scene, on a serious turn, or when the
    listening judge could not read the turn, only the code checks run, and only a redraw is
    logged. Before 2026-10-24 an unread turn skipped the code checks too."""
    m = moment_of(c, t, routed)
    talker = routed.talker
    scene = talker is c.roleplay_talker or m.pretend
    code_only = scene or m.unread_or_heavy
    if not c.on(switch.REDRAW):
        return reply
    if not reply.text.strip():
        return await _redraw_empty(c, t, request, talker)
    if not code_only and not eligible(severity=m.severity, in_scene=False, reply=reply.text):
        return reply
    failed = code_checks(reply.text, t.text, scene=scene)
    if code_only and not failed:
        return reply  # a scene or a serious turn gets only the code checks; a pass is not logged
    detail: dict[str, Json] = {}
    if not failed and c.judge is not None:
        judged = await judge_quip(c.judge, t.text, reply.text)
        if judged is not None:
            detail = {"scorer": judged[1], "prompt": QUIP_PROMPT.ref}
            if judged[0].joke:
                failed.append(QUIP)
            if judged[0].generic:
                failed.append(GENERIC)
    mark(t, f"recheck: {', '.join(failed) or 'passed'}")
    again = None
    if failed:
        again = await talker.reply(request)
        mark_reply(t, again)
        detail |= {"discarded": reply.text, "checks": list[Json](failed)}
        still = [x for x in code_checks(again.text, t.text, scene=scene) if x == DASHED]
        if still and again.text:  # the model that dashes once often dashes again: one more draw
            detail |= {"discarded_again": again.text}
            third = await talker.reply(request)
            mark_reply(t, third)
            again = third if third.text else again
    reason = f"resampled: {', '.join(failed)}" if failed else "kept: the reply passed its checks"
    decide(c, t, RECHECK, detail or None, reason=reason)
    return again if again is not None and again.text else reply


async def checked(
    c: Runtime, t: Turn, request: TalkerRequest, reply: Reply, routed: Routed
) -> Reply:
    """The reply gate: the reply after its checks, in this order. The habit checks (an empty
    reply, then the code checks, then the quip judge), the crisis path's method check
    on a risk turn (ADR 0022), then on a held turn the intimate check and the announced-hold check.
    The first to fail is what the decision logs."""
    talker = routed.talker
    reply = await _habit_checks(c, t, request, reply, routed)
    reply = await method_checked(c, t, lambda: talker.reply(request), reply, routed.crisis)
    if not routed.held:
        return reply
    return await _quiet_hold(c, t, request, await _hold_check(c, t, request, reply, talker), talker)


async def _quiet_hold(
    c: Runtime, t: Turn, request: TalkerRequest, reply: Reply, talker: Talker
) -> Reply:
    """A held reply that says out loud it is holding back ("not real", "keep it pretend") is drawn
    once more. The new one is kept only if it does not announce it too and reads as not intimate;
    otherwise the first stands, so the floor never loosens. Logged either way."""
    if c.judge is None or not reply.text or not announces_limit(reply.text):
        return reply
    again = await talker.reply(request)
    mark_reply(t, again)
    better = not announces_limit(again.text) and await judge_intimate(c.judge, again.text) is False
    decide(
        c,
        t,
        "floor: held reply announced the hold",
        {"first": reply.text, "second": again.text, "kept": "second" if better else "first"},
        reason="floor: a held reply said it was holding back, drawn again; kept the "
        + ("second" if better else "first"),
    )
    return again if better else reply


async def _hold_check(
    c: Runtime, t: Turn, request: TalkerRequest, reply: Reply, talker: Talker
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
            mark_reply(t, reply)
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
