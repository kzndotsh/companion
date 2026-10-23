"""Which talker answers, and the floor no setting moves (ADR 0017).

The roleplay talker is less restrictive than the everyday one. A turn goes to it while a pretend
scene is in progress, or for intimate talk when the operator allows it
(`COMPANION_ROUTE_INTIMATE`). Above both sits a floor in code: romance or sex together with
anything child-like never goes to the less restrictive talker. The listening judge reads every turn
that would be routed, with the recent conversation, and labels it `age_coded`; a yes, or no reading
at all (a failed or late call), keeps the turn on the everyday talker. Doubt never routes. Nothing
carries over by timer: what came up a few messages back is still in the judge's view on the next
turn. A model reads it, because only context tells adults' ordinary pet names and jokes from what
the floor is for; code decides what the label does.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from companion.core.types import Json
from companion.prompts import get


class Talker(StrEnum):
    EVERYDAY = "everyday"
    ROLEPLAY = "roleplay"


@dataclass(frozen=True, slots=True)
class Route:
    talker: Talker
    reason: str | None  # logged when it is not the plain everyday choice

    @property
    def held(self) -> bool:
        """The turn would have gone to the roleplay talker and the floor kept it on the everyday
        one, so its reply is checked before it is sent."""
        return self.talker is Talker.EVERYDAY and self.reason not in (None, STARTING, BRUSHED)


INTIMATE_CHECK = get("system/intimate-check")
HOLD_NOTE = get("notes/floor-hold")
INTIMATE_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"intimate": {"type": "boolean"}},
    "required": ["intimate"],
}


STARTING = "intimate talk starting: the everyday talker answers until it is under way"
EXPLICIT_LEAD = get("system/explicit-lead")
EXPLICIT_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"explicit": {"type": "boolean"}},
    "required": ["explicit"],
}


BRUSHED = "they pushed the flirting back: the everyday talker answers"
BRUSH_OFF = get("system/brush-off")
BRUSH_NOTE = get("notes/brush-off")
BRUSH_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"declines": {"type": "boolean"}},
    "required": ["declines"],
}


def parse_declines(data: Json) -> bool | None:
    value = data.get("declines") if isinstance(data, dict) else None
    return value if isinstance(value, bool) else None


def parse_explicit(data: Json) -> bool | None:
    value = data.get("explicit") if isinstance(data, dict) else None
    return value if isinstance(value, bool) else None


def parse_intimate(data: Json) -> bool | None:
    if not isinstance(data, dict):
        return None
    value = data.get("intimate")
    return value if isinstance(value, bool) else None


def choose(  # noqa: PLR0911, PLR0913  (one rule per route, kept in one place)
    *,
    in_play: bool,
    intimate: bool,
    allow_intimate: bool,
    judged_age_coded: bool | None,
    under_way: bool = True,
    declined: bool = False,
) -> Route:
    """The talker for this turn and why. `judged_age_coded` is None when the judge could not read
    the turn, which keeps it on the everyday talker too. Intimate talk goes to the roleplay talker
    only once it is `under_way` (their message before was intimate too, or this one is explicit):
    a first flirty line gets the everyday talker, so a kiss emoji does not start a scene. When they
    push the flirting or the scene back (`declined`, read by `system/brush-off`), the everyday
    talker answers that turn."""
    if not (in_play or (allow_intimate and intimate)):
        return Route(Talker.EVERYDAY, None)
    if judged_age_coded:
        return Route(
            Talker.EVERYDAY, "floor: kept on the everyday talker, the judge read age-coded content"
        )
    if judged_age_coded is None:
        return Route(
            Talker.EVERYDAY, "kept on the everyday talker: the judge could not read the turn"
        )
    if declined:
        return Route(Talker.EVERYDAY, BRUSHED)
    if in_play:
        return Route(
            Talker.ROLEPLAY, "replied with the roleplay talker: a pretend scene is in progress"
        )
    if not under_way:
        return Route(Talker.EVERYDAY, STARTING)
    return Route(
        Talker.ROLEPLAY,
        "replied with the roleplay talker: intimate talk, which the operator allows",
    )
