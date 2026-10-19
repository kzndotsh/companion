"""Which talker answers, and the floor no setting moves (ADR 0017).

The scene talker is less restrictive than the everyday one. A turn goes to it while a pretend scene
is in progress, or for intimate talk when the operator allows it (`COMPANION_ROUTE_INTIMATE`).
Above both sits a floor in code: romance or sex together with anything child-like never goes to the
less restrictive talker. The listening judge reads every turn that would be routed, with the recent
conversation, and labels it `age_coded`; a yes, or no reading at all (a failed or late call), keeps
the turn on the everyday talker. Doubt never routes. Nothing carries over by timer: what came up a
few messages back is still in the judge's view on the next turn. A model reads it, because only
context tells adults' ordinary pet names and jokes from what the floor is for; code decides what
the label does.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from companion.core.types import Json
from companion.prompts import get


class Talker(StrEnum):
    EVERYDAY = "everyday"
    SCENE = "scene"


@dataclass(frozen=True, slots=True)
class Route:
    talker: Talker
    reason: str | None  # logged when it is not the plain everyday choice

    @property
    def held(self) -> bool:
        """The turn would have gone to the scene talker and the floor kept it on the everyday one,
        so its reply is checked before it is sent."""
        return self.talker is Talker.EVERYDAY and self.reason is not None


INTIMATE_CHECK = get("system/intimate-check")
HOLD_NOTE = get("notes/floor-hold")
PAUSE = get("messages/floor-pause")
INTIMATE_SCHEMA: dict[str, Json] = {
    "type": "object",
    "properties": {"intimate": {"type": "boolean"}},
    "required": ["intimate"],
}


def parse_intimate(data: Json) -> bool | None:
    if not isinstance(data, dict):
        return None
    value = data.get("intimate")
    return value if isinstance(value, bool) else None


def choose(
    *,
    in_play: bool,
    intimate: bool,
    allow_intimate: bool,
    judged_age_coded: bool | None,
) -> Route:
    """The talker for this turn and why. `judged_age_coded` is None when the judge could not read
    the turn, which keeps it on the everyday talker too."""
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
    if in_play:
        return Route(Talker.SCENE, "replied with the scene talker: a pretend scene is in progress")
    return Route(
        Talker.SCENE, "replied with the scene talker: intimate talk, which the operator allows"
    )
