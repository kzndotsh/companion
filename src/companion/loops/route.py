"""The route stage of a turn: which talker answers (ADR 0017), and the reads it waits on."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from companion.core.extractor import from_fallback
from companion.core.floor import BRUSHED, Route
from companion.core.floor import Talker as RouteTalker
from companion.core.floor import choose as choose_route
from companion.core.types import (
    Decision,
    Frame,
    Json,
    Speaker,
)
from companion.loops.floor import DECLINES, EXPLICIT, explicit_lead
from companion.loops.floor import declines as judge_declines
from companion.loops.listen import judge_listening
from companion.loops.turn import Heard, Routed, Turn, decide, mark

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

    def route_for(*, declined: bool = False) -> Route:
        return choose_route(
            in_play=in_play,
            intimate=intimate,
            under_way=under_way,
            allow_intimate=c.route_intimate,
            judged_age_coded=read[0].age_coded
            if read is not None and not from_fallback(read[1])
            else None,
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
    """Whether their message before this one was read as intimate, or answered by the roleplay
    talker: intimate talk already under way."""
    theirs = [u for u in t.prior if u.speaker is Speaker.USER]
    if not theirs:
        return False
    for d in c.store.decisions_for_turn(c.rel, theirs[-1].turn_id):
        if d.has_key("route") and routed_to_roleplay(d):
            return True
        labels = d.detail.get("labels") if d.has_key("listening") and d.detail else None
        if isinstance(labels, dict) and labels.get("intimate") is True:
            return True
    return False


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
