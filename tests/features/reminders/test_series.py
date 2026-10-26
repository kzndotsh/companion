from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from companion.core.types import RelationshipId, TurnId
from companion.features.reminders.logic import (
    Ask,
    Kind,
    Part,
    Reminder,
    Repeat,
    Series,
    Slots,
    Standing,
    parse,
)
from companion.features.reminders.series import (
    HOW_OFTEN,
    Planned,
    first_words,
    next_due,
    repeat_note,
    repeat_of,
    skip_reason,
    tend,
    usual_time,
)

TZ = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 26, 10, 0, tzinfo=TZ)  # a Monday, ten in the morning
DAILY_9 = Repeat(None, time(9))
MORNING = Repeat(None, None, Part.MORNING)
NIGHT = Repeat(None, None, Part.NIGHT)


def _local(day: int, hour: int, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=TZ)


def _series(kind: Kind = Kind.GREETING, repeat: Repeat = MORNING, **kw: object) -> Series:
    return Series(
        "s1",
        RelationshipId("r"),
        kind,
        "good morning",
        "tell me good morning every day",
        repeat,
        "America/New_York",
        TurnId("t"),
        NOW - timedelta(days=5),
        **kw,  # type: ignore[arg-type]
    )


def _occ(seq: int, due: datetime, state: str, at: datetime | None = None) -> Reminder:
    return Reminder(
        f"o{seq}",
        RelationshipId("r"),
        Kind.GREETING,
        "good morning",
        "q",
        due,
        "",
        "America/New_York",
        TurnId("t"),
        due - timedelta(days=1),
        state,
        "s1",
        seq,
        at or due,
    )


def test_daily_and_weekly_keep_the_wall_time_across_the_clock_change() -> None:
    before = _local(31, 10)  # Saturday, the day before the clocks go back
    sunday = next_due(DAILY_9, time(9), before, TZ, None)
    assert sunday.astimezone(TZ) == _local(1, 9, month=11)
    assert sunday.astimezone(UTC).hour == 14  # 9 am EST; it was 13:00 UTC the day before
    monday = next_due(Repeat(0, time(9)), time(9), NOW, TZ, None)  # Monday at ten: next week's
    assert monday.astimezone(TZ) == _local(2, 9, month=11)
    assert monday.astimezone(UTC).hour == 14


def test_a_daily_one_said_after_its_time_goes_tomorrow_and_before_it_today() -> None:
    assert next_due(DAILY_9, time(9), NOW, TZ, None) == _local(27, 9)
    assert next_due(DAILY_9, time(11), NOW, TZ, None) == _local(26, 11)
    friday = next_due(Repeat(4, time(18)), time(18), NOW, TZ, None)
    assert friday == _local(30, 18)


def test_a_learned_time_that_moved_later_never_sends_twice_in_a_day() -> None:
    sent_at_8 = _local(26, 8)
    later = next_due(MORNING, time(8, 30), _local(26, 8, 1), TZ, sent_at_8)
    assert later == _local(27, 8, 30)


def _days(*clock: tuple[int, int, int]) -> list[datetime]:
    return [_local(day, hour, minute) for day, hour, minute in clock]


def test_a_morning_greeting_learns_the_median_first_message_rounded_to_five_minutes() -> None:
    theirs = _days(
        (20, 7, 52), (20, 12, 0),  # first at 7:52
        (21, 8, 13), (21, 9, 0),  # 8:13
        (22, 1, 30),  # after midnight: the end of the 21st, not the start of the 22nd
        (22, 8, 21),  # 8:21
    )  # fmt: skip
    assert usual_time(Part.MORNING, theirs, NOW, TZ) == time(8, 15)


def test_a_morning_greeting_with_under_three_days_of_messages_goes_at_nine() -> None:
    theirs = _days((20, 7, 0), (21, 7, 0))
    assert usual_time(Part.MORNING, theirs, NOW, TZ) == time(9)
    old = _days((1, 7, 0), (2, 7, 0), (3, 7, 0))  # more than fourteen days back
    assert usual_time(Part.MORNING, old, NOW, TZ) == time(9)


def test_a_night_greeting_learns_the_last_message_past_midnight_and_not_today() -> None:
    theirs = _days(
        (21, 20, 0), (21, 23, 40),
        (22, 21, 0), (23, 0, 30),  # the 22nd ended at half past midnight
        (23, 22, 0), (24, 1, 10),
    )  # fmt: skip
    assert usual_time(Part.NIGHT, theirs, NOW, TZ) == time(0, 30)
    today_not_over = _days((24, 23, 0), (25, 23, 0), (26, 9, 30))  # NOW is the 26th, 10 am
    assert usual_time(Part.NIGHT, today_not_over, NOW, TZ) == time(22)  # two days: the default


def test_a_morning_greeting_is_skipped_when_they_wrote_first_that_morning() -> None:
    due = _local(26, 8, 30)
    s = _series()
    assert skip_reason(s, due, _days((26, 7, 0)), due, TZ) == "they already wrote today"
    assert skip_reason(s, due, _days((26, 2, 0)), due, TZ) is None  # last night, not this morning
    assert skip_reason(s, due, [], due, TZ) is None


def test_a_night_greeting_is_skipped_only_after_a_message_in_the_two_hours_before() -> None:
    due = _local(26, 22)
    s = _series(repeat=NIGHT)
    assert skip_reason(s, due, _days((26, 21, 0)), due, TZ) is not None
    assert skip_reason(s, due, _days((26, 19, 0)), due, TZ) is None


def test_a_reminder_or_check_in_is_never_skipped() -> None:
    due = _local(26, 8, 30)
    for kind in (Kind.REMINDER, Kind.CHECK_IN):
        s = _series(kind, Repeat(None, time(8, 30)))
        assert skip_reason(s, due, _days((26, 8, 29)), due, TZ) is None


def test_three_greetings_sent_since_they_last_wrote_pause_and_their_message_resumes() -> None:
    sent = [_occ(n, _local(22 + n, 9), "sent") for n in (1, 2, 3)]
    theirs = _days((22, 20, 0))
    paused = tend(_series(), sent, theirs, NOW, TZ)
    assert (paused.state, paused.due) == (Standing.PAUSED, None)
    two = tend(_series(), sent[:2], theirs, NOW, TZ)
    assert two.state is None
    assert two.due is not None
    back = tend(_series(state=Standing.PAUSED), sent, [*theirs, NOW], NOW, TZ)
    assert back.state is Standing.ACTIVE
    assert back.due is not None
    assert back.seq == 4


def test_a_reminder_series_never_pauses() -> None:
    sent = [_occ(n, _local(22 + n, 9), "sent") for n in (1, 2, 3, 4)]
    step = tend(_series(Kind.REMINDER, DAILY_9), sent, [], NOW, TZ)
    assert step.state is None
    assert step.due == _local(27, 9)


def test_tending_makes_nothing_while_one_is_pending_or_once_stopped() -> None:
    pending = [_occ(1, _local(27, 9), "pending")]
    assert tend(_series(), pending, [], NOW, TZ).due is None
    assert tend(_series(), [_occ(1, _local(26, 9), "claimed")], [], NOW, TZ).due is None
    assert tend(_series(state=Standing.STOPPED), [], [], NOW, TZ).due is None
    first = tend(_series(Kind.REMINDER, DAILY_9), [], [], NOW, TZ)
    assert (first.seq, first.due) == (1, _local(27, 9))
    after_skip = tend(_series(), [_occ(1, _local(26, 9), "skipped")], [], NOW, TZ)
    assert after_skip.seq == 2


def _ask(**kw: object) -> Slots:
    kind = Kind(str(kw.pop("kind", "greeting")))
    thing = str(kw.pop("thing", "good morning"))
    return Slots(Ask.SET, kind, thing, repeats=True, **kw)  # type: ignore[arg-type]


def test_how_a_repeating_request_is_read() -> None:
    assert repeat_of(_ask(every="day"), NOW, TZ) == Planned(MORNING)
    assert repeat_of(_ask(thing="goodnight", every="day"), NOW, TZ) == Planned(NIGHT)
    at_7 = repeat_of(_ask(every="day", hour=7, minute=30), NOW, TZ)
    assert at_7 == Planned(Repeat(None, time(7, 30), Part.MORNING))
    meds = repeat_of(_ask(kind="reminder", thing="meds", every="day", hour=8, ampm="pm"), NOW, TZ)
    assert meds == Planned(Repeat(None, time(20)))
    friday = _ask(kind="reminder", thing="bins", day="weekday", weekday="friday", hour=7, ampm="am")
    assert repeat_of(friday, NOW, TZ) == Planned(Repeat(4, time(7)))
    assert repeat_of(_ask(kind="reminder", thing="meds", every="day"), NOW, TZ) == "what time"
    evening = repeat_of(_ask(kind="reminder", thing="meds", every="day", part="evening"), NOW, TZ)
    assert evening == Planned(Repeat(None, time(18)), defaulted=True)
    assert repeat_of(_ask(kind="reminder", thing="x", every="other", hour=9), NOW, TZ) == HOW_OFTEN
    bare = repeat_of(_ask(kind="reminder", thing="meds", every="day", hour=8), NOW, TZ)
    assert bare == "whether they meant 8 in the morning or the evening"


def test_the_reader_answer_with_a_greeting_and_how_often_is_parsed_and_an_old_one_still_is() -> (
    None
):
    base: dict[str, object] = {
        "ask": "set",
        "kind": "greeting",
        "thing": "good morning",
        "day": "unsaid",
        "ampm": "unsaid",
        "part": "morning",
        "repeats": True,
    }
    s = parse({**base, "every": "Monday"})  # type: ignore[arg-type]
    assert s is not None
    assert (s.kind, s.every, s.repeats) == (Kind.GREETING, "monday", True)
    old = parse({**base, "kind": "reminder"})  # type: ignore[arg-type]
    assert old is not None
    assert old.every == "unsaid"
    odd = parse({**base, "every": "fortnightly"})  # type: ignore[arg-type]
    assert odd is not None
    assert odd.every == "other"


def test_the_set_note_says_how_often_and_a_learned_time_by_their_day_not_a_clock_time() -> None:
    daily = repeat_note(
        Kind.REMINDER, "meds", Planned(Repeat(None, time(20))), "tonight at 8:00 pm"
    )
    assert "remind them about meds, every day at 8:00 pm" in daily
    assert "the first one is tonight at 8:00 pm" in daily
    assert "Never say you cannot send it" in daily
    weekly = repeat_note(Kind.REMINDER, "bins", Planned(Repeat(4, time(7))), "x")
    assert "every Friday at 7:00 am" in weekly
    due = _local(27, 8, 15)
    learned = repeat_note(
        Kind.GREETING, "good morning", Planned(MORNING), first_words(MORNING, due, NOW, TZ)
    )
    assert "say good morning to them, every morning, around when they usually start" in learned
    assert "the first one is tomorrow morning" in learned
    assert "8:15" not in learned
    assert "Name no clock time" in learned
    night = first_words(NIGHT, _local(26, 23), NOW, TZ)
    assert night == "tonight"
