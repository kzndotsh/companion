from __future__ import annotations

import pytest

from companion.core.floor import Talker, choose


def _route(**over: object) -> Talker:
    base: dict[str, object] = {
        "in_play": False,
        "intimate": False,
        "allow_intimate": False,
        "judged_age_coded": False,
    }
    return choose(**{**base, **over}).talker  # pyright: ignore[reportArgumentType]


def test_a_scene_goes_to_the_scene_talker_and_intimate_talk_only_when_allowed() -> None:
    assert _route(in_play=True) is Talker.SCENE
    assert _route(intimate=True) is Talker.EVERYDAY
    assert _route(intimate=True, allow_intimate=True) is Talker.SCENE
    assert _route() is Talker.EVERYDAY


@pytest.mark.parametrize(
    "held",
    [
        {"judged_age_coded": True},
    ],
)
def test_the_floor_keeps_both_routes_on_the_everyday_talker(held: dict[str, object]) -> None:
    assert _route(in_play=True, **held) is Talker.EVERYDAY
    assert _route(intimate=True, allow_intimate=True, **held) is Talker.EVERYDAY


def test_a_floor_trip_and_a_missing_reading_are_logged_and_a_plain_turn_is_not() -> None:
    def route(**over: object) -> str | None:
        base: dict[str, object] = {
            "in_play": True,
            "intimate": False,
            "allow_intimate": False,
            "judged_age_coded": False,
        }
        return choose(**{**base, **over}).reason  # pyright: ignore[reportArgumentType]

    assert route(judged_age_coded=True) == (
        "floor: kept on the everyday talker, the judge read age-coded content"
    )
    assert route(judged_age_coded=None) == (
        "kept on the everyday talker: the judge could not read the turn"
    )
    assert route(in_play=False, judged_age_coded=True) is None
