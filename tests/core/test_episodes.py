from __future__ import annotations

from datetime import timedelta

from companion.core.episodes import Kind, Stretch, firsts, kind, stretches
from companion.core.types import (
    Frame,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from tests.conftest import T0


def _said(n: int, minutes: float, frame: Frame = Frame.REAL) -> Utterance:
    return Utterance(
        UtteranceId(f"u{n}"),
        RelationshipId("r"),
        SessionId("s"),
        TurnId(f"t{n}"),
        Speaker.USER if n % 2 == 0 else Speaker.COMPANION,
        "hi",
        frame,
        "t",
        T0 + timedelta(minutes=minutes),
    )


def test_a_gap_of_two_hours_starts_a_new_stretch() -> None:
    said = [_said(0, 0), _said(1, 5), _said(2, 5 + 120), _said(3, 130)]
    assert [len(s.said) for s in stretches(said)] == [2, 2]


def test_a_long_turn_into_a_scene_starts_one_but_a_short_one_does_not() -> None:
    real = [_said(i, i) for i in range(22)]
    scene = [_said(22 + i, 22 + i, Frame.PLAY) for i in range(22)]
    assert [len(s.said) for s in stretches([*real, *scene])] == [22, 22]
    blip = [_said(22 + i, 22 + i, Frame.PLAY) for i in range(3)]
    after = [_said(25 + i, 25 + i) for i in range(22)]
    assert [len(s.said) for s in stretches([*real, *blip, *after])] == [47]


def test_heavy_wins_then_scene_then_everyday_and_firsts_are_named_once() -> None:
    scene = Stretch(tuple(_said(i, i, Frame.PLAY) for i in range(4)))
    assert kind(scene, {}) is Kind.SCENE
    assert kind(scene, {TurnId("t0"): 2}) is Kind.HEAVY
    assert kind(Stretch((_said(0, 0),)), {}) is Kind.EVERYDAY
    assert firsts(Kind.SCENE, set()) == ["first pretend scene"]
    assert firsts(Kind.SCENE, {Kind.SCENE}) == []
    assert firsts(Kind.EVERYDAY, set()) == []


def test_a_line_longer_than_a_summary_is_not_kept() -> None:
    from companion.core.episodes import MAX_WORDS, parse  # noqa: PLC0415

    assert parse({"gist": " A cozy  evening. "}) == "A cozy evening."
    assert parse({"gist": "word " * (MAX_WORDS + 1)}) is None
    assert parse({"gist": ""}) is None


def test_words_point_at_a_time_from_a_seven_oclock_day() -> None:
    from datetime import datetime  # noqa: PLC0415
    from zoneinfo import ZoneInfo  # noqa: PLC0415

    from companion.core.episodes import period, when_said  # noqa: PLC0415

    z = ZoneInfo("America/New_York")
    evening = datetime(2026, 10, 21, 20, 43, tzinfo=z)
    night = period("still drained from last night", evening, z)
    assert night == (datetime(2026, 10, 20, 18, tzinfo=z), datetime(2026, 10, 21, 7, tzinfo=z))
    small_hours = datetime(2026, 10, 19, 3, 6, tzinfo=z)
    day = period("it was an intense day", small_hours, z)
    assert day == (datetime(2026, 10, 18, 7, tzinfo=z), small_hours)  # at 3 a.m. "today" is ending
    assert period("hey", evening, z) is None
    assert when_said(datetime(2026, 10, 21, 2, 42, tzinfo=z), evening, z) == "last night"
    assert when_said(datetime(2026, 10, 18, 10, tzinfo=z), small_hours, z) == "earlier today"
    assert when_said(datetime(2026, 10, 19, 0, 41, tzinfo=z), small_hours, z) == "earlier tonight"


def test_recent_shows_the_time_pointed_at_else_the_last_one_after_a_gap() -> None:
    from datetime import datetime  # noqa: PLC0415
    from zoneinfo import ZoneInfo  # noqa: PLC0415

    from companion.core.episodes import recent  # noqa: PLC0415

    z = ZoneInfo("America/New_York")
    ends = [
        (
            datetime(2026, 10, 20, 22, tzinfo=z),
            datetime(2026, 10, 21, 0, 30, tzinfo=z),
            "a late one",
        ),
        (
            datetime(2026, 10, 21, 13, tzinfo=z),
            datetime(2026, 10, 21, 17, tzinfo=z),
            "an easy afternoon",
        ),
    ]
    now = datetime(2026, 10, 21, 20, 43, tzinfo=z)
    assert [t.gist for t in recent(ends, "drained from last night", now, now, z)] == ["a late one"]
    back = recent(ends, "hey", datetime(2026, 10, 21, 17, tzinfo=z), now, z)
    assert [(t.when, t.gist) for t in back] == [("earlier today", "an easy afternoon")]
    assert recent(ends, "hey", now - timedelta(minutes=5), now, z) == []
