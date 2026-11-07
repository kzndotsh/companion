"""The route stage of a turn: which talker answers (ADR 0017), and the reads it waits on."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from companion.core import switch
from companion.core.episode import EPISODE_GAP
from companion.core.extractor import from_fallback
from companion.core.turn.floor import BRUSH_KEY, MINOR_KEY, Route
from companion.core.turn.floor import Talker as RouteTalker
from companion.core.turn.floor import choose as choose_route
from companion.core.types import (
    Decision,
    Frame,
    Json,
    Speaker,
)
from companion.kit.current import Heard, Turn, decide, mark
from companion.turn.floor import DECLINES, EXPLICIT, MINOR, confirm_minor, explicit_lead
from companion.turn.floor import declines as judge_declines
from companion.turn.listen import judge_listening
from companion.turn.values import Routed

if TYPE_CHECKING:
    from companion.kit.runtime import Runtime

log = logging.getLogger("companion.turn")
# How many of their messages back intimate talk counts as under way: one held or brushed-off turn
# in the middle of a scene reset it, and the everyday talker answered the next turn as if it were
# only starting (owner flag 2026-11-05).
UNDER_WAY_LOOKBACK = 6


async def route_turn(c: Runtime, t: Turn, in_scene: Frame, heard: Heard | None) -> Routed:
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
    if intimate and c.on(switch.ROUTE_INTIMATE) and not in_play:
        under_way = _intimate_before(c, t) or await _explicit(c, t)

    # The fallback model's age read is never trusted (ADR 0017), so a read from it is unsure, and an
    # unsure read goes to the narrow minor check like a yes: only that check's yes, or no reading,
    # holds the turn. Before, a refusal by the judge model held the turn outright, mid-scene
    # (owner flag 2026-11-05).
    unsure = read is not None and from_fallback(read[1])
    age_coded = read[0].age_coded if read is not None and not unsure else None
    if (age_coded or unsure) and (in_play or (c.on(switch.ROUTE_INTIMATE) and intimate)):
        age_coded = await _minor(c, t, unsure=unsure)

    def route_for(*, declined: bool = False) -> Route:
        return choose_route(
            in_play=in_play,
            intimate=intimate,
            under_way=under_way,
            allow_intimate=c.on(switch.ROUTE_INTIMATE),
            judged_age_coded=age_coded,
            declined=declined,
        )

    route = route_for()
    if route.talker is RouteTalker.ROLEPLAY and await _declines(c, t):
        route = route_for(declined=True)
    if route.reason is not None:
        detail: dict[str, Json] = {"talker": route.talker.value}
        if route.because is not None:
            detail["because"] = route.because
        decide(c, t, "route", detail, reason=route.reason)
    talker = c.roleplay_talker if route.talker is RouteTalker.ROLEPLAY else c.talker
    return Routed(
        talker,
        held=route.held,
        read=read,
        brushed=route.brushed,
        heard=heard,
        in_scene=in_scene,
    )


def routed_to_roleplay(d: Decision) -> bool:
    """Whether a route decision sent the turn to the roleplay talker. Read from its detail; a
    decision from before the detail was kept matches by how its reason begins."""
    if isinstance(d.detail, dict) and "talker" in d.detail:
        return d.detail["talker"] == RouteTalker.ROLEPLAY.value
    return d.reason.startswith("replied with the roleplay talker")


def route_because(d: Decision) -> str:
    """What sent the turn to the roleplay talker, from the route decision's detail; one logged
    before that was kept has it after the first colon of its reason."""
    if isinstance(d.detail, dict) and isinstance(d.detail.get("because"), str):
        return str(d.detail["because"])
    return d.reason.partition(": ")[2] or "routed there"


async def _minor(c: Runtime, t: Turn, *, unsure: bool = False) -> bool | None:
    """The listening judge read the turn as age-coded, or only the fallback model read it: ask the
    narrow minor check. Only its yes, or no reading, holds the turn; with no reading, a turn read
    only by the fallback model is held as unread (None), not as age-coded."""
    if c.judge is None:
        return None if unsure else True
    mark(t, "minor check")
    got = await confirm_minor(c.judge, t.prior, t.text)
    held = got is None or got.value
    detail: dict[str, Json] = {"minor": held, "read": got is not None, "prompt": MINOR.prompt.ref}
    if got is not None:
        detail["scorer"] = got.model
    decide(c, t, MINOR_KEY, detail)
    return None if unsure and got is None else held


async def _declines(c: Runtime, t: Turn) -> bool:
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
    decide(c, t, BRUSH_KEY, detail)
    return found


def _intimate_before(c: Runtime, t: Turn) -> bool:
    """Whether one of their last few messages, within an episode, was answered by the roleplay
    talker: intimate talk already under way. Flirting before it does not count, since a run of
    flirty lines reads as intimate (2026-10-24); only an explicit message starts it, and then it
    carries on, past a held or brushed-off turn in the middle."""
    theirs = [u for u in t.prior if u.speaker is Speaker.USER and t.now - u.at < EPISODE_GAP][
        -UNDER_WAY_LOOKBACK:
    ]
    return any(
        d.has_key("route") and routed_to_roleplay(d)
        for u in theirs
        for d in c.store.decisions_for_turn(c.rel, u.turn_id)
    )


async def _explicit(c: Runtime, t: Turn) -> bool:
    """Whether their message itself is sexually explicit: then intimacy starts on the roleplay
    talker at once. A failed read is no."""
    if c.judge is None:
        return False
    mark(t, "explicit-lead judge")
    got = await explicit_lead(c.judge, t.prior, t.text)
    found = got is not None and got.value
    decide(c, t, "explicit lead", {"explicit": found, "prompt": EXPLICIT.prompt.ref})
    return found
