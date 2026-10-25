from __future__ import annotations

from datetime import timedelta

from companion.core.reachout import Held
from companion.core.turn.now import Label, Phase, Said
from companion.features.nudges.logic import Away, Look, aways, due, wait
from tests.conftest import T0

SHOWER = Away("t1", "shower time now", 30, T0)


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
    assert wait(Away("t", "errand", 50, T0)) == timedelta(minutes=100)
    assert due(_look(), T0 + timedelta(minutes=50), None)[1] == "not long enough yet"
    assert due(_look(), T0 + timedelta(minutes=70), None)[0] == SHOWER


def test_anything_from_them_or_a_past_nudge_or_the_day_cap_holds_it() -> None:
    later = T0 + timedelta(minutes=90)
    assert due(_look(last_theirs=T0 + timedelta(minutes=5)), later, None)[1] == "they came back"
    assert due(_look(nudged=frozenset({"t1"})), later, None)[1] == "already nudged about it"
    assert due(_look(nudges_today=2), later, None)[1] == "already 2 today"
    assert due(_look(), T0 + timedelta(hours=7), None)[1] == "gone too long; past nudging"
    assert due(_look(away=None), later, None)[1] == "no time away"


def test_a_time_away_is_a_leaving_label_and_nothing_else() -> None:
    leaving = Said(Label(Phase.LEAVING, "they will shower", 30), "shower time now", "t1", T0)
    soon = Said(Label(Phase.SOON, "dinner is coming soon", 30), "dinner soon", "t2", T0)
    assert aways([leaving, soon]) == [SHOWER]


def test_the_shared_gate_holds_it_with_its_reason_once_it_is_due() -> None:
    quiet = Held("quiet hours", "3:00 is one of their quiet hours")
    assert due(_look(), T0 + timedelta(minutes=70), quiet) == (None, quiet.why)
    assert due(_look(), T0 + timedelta(minutes=50), quiet)[1] == "not long enough yet"
