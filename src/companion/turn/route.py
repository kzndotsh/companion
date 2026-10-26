"""The route stage of a turn: which talker answers (ADR 0017), and the reads it waits on."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from companion.core.extractor import from_fallback
from companion.core.turn.floor import BRUSHED, Route
from companion.core.turn.floor import Talker as RouteTalker
from companion.core.turn.floor import choose as choose_route
from companion.core.types import (
    Decision,
    Frame,
    Json,
    Speaker,
)
from companion.loops.current import Heard, Turn, decide, mark
from companion.turn.floor import DECLINES, EXPLICIT, MINOR, confirm_minor, explicit_lead
from companion.turn.floor import declines as judge_declines
from companion.turn.listen import judge_listening
from companion.turn.values import Routed

if TYPE_CHECKING:
    from companion.loops.conversation import Conversation

log = logging.getLogger("companion.turn")


async def route_turn(c: Conversation, t: Turn, in_scene: Frame, heard: Heard | None) -> Routed:
    """The talker for this turn (ADR 0017): the roleplay talker for a pretend scene, or for intimate
    talk when COMPANION_ROUTE_INTIMATE allows it, unless the floor keeps it on the everyday talker.
    Logged when it is anything but the plain everyday choice.

    The listening judge does not run in a scene, so a scene turn is read here, for routing only.
    The frame is the one the previous turn left, so the first message of a scene is answered by
    the everyday talker and the next ones by the roleplay talker. Returns that read too, so a
    scene turn can still look something up when they say it forgot.
    """
    if c.roleplay_talker is None:
        return Routed(
            c.talker, held=False, read=heard, brushed=False, heard=heard, in_scene=in_scene
        )
    in_play = in_scene is Frame.PLAY
    read = heard
    if read is None and in_play and c.judge is not None:
        mark(t, "floor: reading the scene turn")
        read = await judge_listening(c.judge, t.prior, t.text)  # for routing only, no note
    intimate = read is not None and read[0].intimate
    under_way = True
    if intimate and c.route_intimate and not in_play:
        under_way = _intimate_before(c, t) or await _explicit(c, t)

    age_coded = read[0].age_coded if read is not None and not from_fallback(read[1]) else None
    if age_coded and (in_play or (c.route_intimate and intimate)):
        age_coded = await _minor(c, t)

    def route_for(*, declined: bool = False) -> Route:
        return choose_route(
            in_play=in_play,
            intimate=intimate,
            under_way=under_way,
            allow_intimate=c.route_intimate,
            judged_age_coded=age_coded,
            declined=declined,
        )

    route = route_for()
    if route.talker is RouteTalker.ROLEPLAY and await _declines(c, t):
        route = route_for(declined=True)
    if route.reason is not None:
        decide(c, t, "route", {"talker": route.talker.value}, reason=route.reason)
    talker = c.roleplay_talker if route.talker is RouteTalker.ROLEPLAY else c.talker
    return Routed(
        talker,
        held=route.held,
        read=read,
        brushed=route.reason == BRUSHED,
        heard=heard,
        in_scene=in_scene,
    )


def routed_to_roleplay(d: Decision) -> bool:
    """Whether a route decision sent the turn to the roleplay talker. Read from its detail; a
    decision from before the detail was kept matches by how its reason begins."""
    if isinstance(d.detail, dict) and "talker" in d.detail:
        return d.detail["talker"] == RouteTalker.ROLEPLAY.value
    return d.reason.startswith("replied with the roleplay talker")


async def _minor(c: Conversation, t: Turn) -> bool:
    """The listening judge read the turn as age-coded: ask the narrow minor check. Only its yes, or
    no reading, holds the turn."""
    if c.judge is None:
        return True
    mark(t, "minor check")
    got = await confirm_minor(c.judge, t.prior, t.text)
    held = got is None or got.value
    detail: dict[str, Json] = {"minor": held, "read": got is not None, "prompt": MINOR.prompt.ref}
    if got is not None:
        detail["scorer"] = got.model
    decide(c, t, "minor check", detail)
    return held


async def _declines(c: Conversation, t: Turn) -> bool:
    """Whether their message pushes the flirting or the scene back, asked only of a turn the
    roleplay talker would answer. A failed read is no: the turn goes where it would have."""
    if c.judge is None:
        return False
    mark(t, "brush-off judge")
    got = await judge_declines(c.judge, t.prior, t.text)
    found = got is not None and got.value
    detail: dict[str, Json] = {"declines": found, "prompt": DECLINES.prompt.ref}
    if got is not None:
        detail["scorer"] = got.model
    decide(c, t, "brush-off", detail)
    return found


def _intimate_before(c: Conversation, t: Turn) -> bool:
    """Whether their message before this one was answered by the roleplay talker: intimate talk
    already under way. Flirting before it does not count, since a run of flirty lines reads as
    intimate (2026-10-24); only an explicit message starts it, and then it carries on."""
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs:
        return False
    return any(
        d.has_key("route") and routed_to_roleplay(d)
        for d in c.store.decisions_for_turn(c.rel, theirs[-1].turn_id)
    )


async def _explicit(c: Conversation, t: Turn) -> bool:
    """Whether their message itself is sexually explicit: then intimacy starts on the roleplay
    talker at once. A failed read is no."""
    if c.judge is None:
        return False
    mark(t, "explicit-lead judge")
    got = await explicit_lead(c.judge, t.prior, t.text)
    found = got is not None and got.value
    decide(c, t, "explicit lead", {"explicit": found, "prompt": EXPLICIT.prompt.ref})
    return found
