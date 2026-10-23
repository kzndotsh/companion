from __future__ import annotations

from datetime import UTC, timedelta

from companion.features.nudges.logic import Away, Kind, Look, due, parse, wait
from tests.conftest import T0

SHOWER = Away("t1", "shower time now", Kind.BRIEF, 30, T0)


def _look(**kw: object) -> Look:
    base: dict[str, object] = {
        "away": SHOWER,
        "last_theirs": T0,
        "nudged": frozenset(),
        "nudges_today": 0,
    }
    return Look(**{**base, **kw})  # type: ignore[arg-type]


def test_a_nudge_waits_twice_the_time_away_and_an_hour_at_least() -> None:
    assert wait(SHOWER) == timedelta(hours=1)
    assert wait(Away("t", "errand", Kind.BRIEF, 50, T0)) == timedelta(minutes=100)
    assert due(_look(), T0 + timedelta(minutes=50), UTC)[1] == "not long enough yet"
    assert due(_look(), T0 + timedelta(minutes=70), UTC)[0] == SHOWER


def test_anything_from_them_or_a_past_nudge_or_the_day_cap_holds_it() -> None:
    later = T0 + timedelta(minutes=90)
    assert due(_look(last_theirs=T0 + timedelta(minutes=5)), later, UTC)[1] == "they came back"
    assert due(_look(nudged=frozenset({"t1"})), later, UTC)[1] == "already nudged about it"
    assert due(_look(nudges_today=2), later, UTC)[1] == "already 2 today"
    assert due(_look(), T0 + timedelta(hours=7), UTC)[1] == "gone too long; past nudging"
    assert due(_look(away=None), later, UTC)[1] == "no time away"


def test_only_stepping_away_is_read_and_minutes_are_clamped() -> None:
    assert parse({"away": "brief", "minutes": 500}) == (Kind.BRIEF, 180)
    assert parse({"away": "back", "minutes": 2}) == (Kind.BACK, 10)
    assert parse({"away": "goodbye", "minutes": 30}) is None
    assert parse({"away": "none", "minutes": 0}) is None
    assert parse({"away": "brief", "minutes": True}) is None
