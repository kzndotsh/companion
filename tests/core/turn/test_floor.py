from __future__ import annotations

import pytest

from companion.core.turn.floor import Talker, choose


def _route(**over: object) -> Talker:
    base: dict[str, object] = {
        "in_play": False,
        "intimate": False,
        "allow_intimate": False,
        "judged_age_coded": False,
    }
    return choose(**{**base, **over}).talker  # pyright: ignore[reportArgumentType]


def test_a_scene_goes_to_the_roleplay_talker_and_intimate_talk_only_when_allowed() -> None:
    assert _route(in_play=True) is Talker.ROLEPLAY
    assert _route(intimate=True) is Talker.EVERYDAY
    assert _route(intimate=True, allow_intimate=True) is Talker.ROLEPLAY
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


def test_intimate_talk_waits_until_it_is_under_way_but_a_scene_never_does() -> None:
    from companion.core.turn.floor import STARTING  # noqa: PLC0415

    starting = choose(
        in_play=False, intimate=True, allow_intimate=True, judged_age_coded=False, under_way=False
    )
    assert starting.talker is Talker.EVERYDAY
    assert starting.reason == STARTING
    assert not starting.held  # not the floor: no hold note, no intimate check on the reply
    scene = choose(
        in_play=True, intimate=True, allow_intimate=True, judged_age_coded=False, under_way=False
    )
    assert scene.talker is Talker.ROLEPLAY


def test_a_push_back_goes_to_the_everyday_talker_without_a_hold_but_the_floor_comes_first() -> None:
    from companion.core.turn.floor import BRUSHED  # noqa: PLC0415

    def route(**over: object):
        base: dict[str, object] = {
            "in_play": True,
            "intimate": False,
            "allow_intimate": True,
            "judged_age_coded": False,
            "declined": True,
        }
        return choose(**{**base, **over})  # pyright: ignore[reportArgumentType]

    pushed = route()
    assert (pushed.talker, pushed.reason, pushed.held) == (Talker.EVERYDAY, BRUSHED, False)
    assert route(in_play=False, intimate=True).reason == BRUSHED
    assert route(judged_age_coded=True).held  # the floor's own hold, with its check
    assert route(declined=False).talker is Talker.ROLEPLAY
