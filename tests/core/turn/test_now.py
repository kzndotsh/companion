from __future__ import annotations

from datetime import UTC, datetime, timedelta

from companion.core.turn.now import Label, Phase, Said, ago, open_now, parse, soon_note

T0 = datetime(2026, 10, 25, 22, 12, tzinfo=UTC)
DINNER = Label(Phase.SOON, "dinner is coming soon", 30)


def _said(label: Label, minutes: float) -> Said:
    return Said(label, "words", "t", T0 + timedelta(minutes=minutes))


def test_a_label_is_read_clamped_and_one_that_opens_needs_a_what() -> None:
    assert parse({"now": "soon", "what": " dinner  is coming ", "minutes": 900}) == Label(
        Phase.SOON, "dinner is coming", 180
    )
    assert parse({"now": "soon", "what": "", "minutes": 30}) is None
    assert parse({"now": "done", "what": "", "minutes": 0}) == Label(Phase.DONE, "", 5)
    assert parse({"now": "later", "what": "x", "minutes": 3}) is None
    assert parse("junk") is None


def test_what_they_said_is_coming_stays_open_until_they_say_it_happened() -> None:
    dinner = _said(DINNER, 0)
    assert open_now([dinner], T0 + timedelta(minutes=2)) == [dinner]
    came = _said(Label(Phase.DONE, "", 5), 20)
    assert open_now([dinner, came], T0 + timedelta(minutes=21)) == []
    back = _said(Label(Phase.BACK, "", 5), 40)
    shower = _said(Label(Phase.LEAVING, "they will shower", 30), 30)
    assert open_now([dinner, shower, back], T0 + timedelta(minutes=41)) == []


def test_an_item_closes_once_well_past_its_time() -> None:
    dinner = _said(DINNER, 0)
    assert open_now([dinner], T0 + timedelta(minutes=89))
    assert not open_now([dinner], T0 + timedelta(minutes=91))
    quick = _said(Label(Phase.SOON, "coffee is brewing", 5), 0)
    assert open_now([quick], T0 + timedelta(minutes=19))  # never under 20 minutes
    assert not open_now([quick], T0 + timedelta(minutes=21))


def test_the_note_states_the_newest_soon_item_and_nothing_for_leaving() -> None:
    later = T0 + timedelta(minutes=2)
    assert soon_note([_said(DINNER, 0)], later) == (
        "[About 2 minutes ago they said dinner is coming soon."
        " It has not happened yet unless they say so.]"
    )
    assert soon_note([_said(Label(Phase.LEAVING, "they will shower", 30), 0)], later) is None
    assert soon_note([], later) is None
    assert ago(timedelta(seconds=40)) == "a minute"
    assert ago(timedelta(minutes=70)) == "an hour"
