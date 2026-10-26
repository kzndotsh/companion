from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from random import Random
from zoneinfo import ZoneInfo

from companion.features.reminders.logic import (
    Ask,
    Kind,
    Slots,
    likely,
    matching,
    parse,
    resolve,
    spoken,
)

TZ = ZoneInfo("America/New_York")
NOW = datetime(2026, 10, 19, 10, 0, tzinfo=TZ)  # a Monday, ten in the morning


def _set(**kw: object) -> Slots:
    return Slots(Ask.SET, Kind(str(kw.pop("kind", "reminder"))), "the dog", **kw)  # type: ignore[arg-type]


def _at(**kw: object) -> datetime | None:
    return resolve(_set(**kw), NOW, TZ).at


def test_a_bare_hour_is_the_next_one_still_to_come_and_asked_when_both_are() -> None:
    assert _at(hour=8) == datetime(2026, 10, 19, 20, 0, tzinfo=TZ)  # 8 am has gone
    eleven = resolve(_set(hour=11), NOW, TZ)
    assert eleven.at is None
    assert "morning or the evening" in eleven.unclear


def test_a_bare_hour_on_another_day_is_asked_but_a_part_of_day_settles_it() -> None:
    assert _at(day="tomorrow", hour=8) is None
    assert _at(day="tomorrow", hour=8, part="morning") == datetime(2026, 10, 20, 8, tzinfo=TZ)
    assert _at(day="tonight", hour=9) == datetime(2026, 10, 19, 21, tzinfo=TZ)


def test_am_pm_and_the_24_hour_clock_are_read_as_said() -> None:
    assert _at(hour=8, ampm="pm") == datetime(2026, 10, 19, 20, tzinfo=TZ)
    assert _at(hour=12, ampm="am", day="tomorrow") == datetime(2026, 10, 20, 0, tzinfo=TZ)
    assert _at(hour=20, minute=30) == datetime(2026, 10, 19, 20, 30, tzinfo=TZ)


def test_minutes_from_now() -> None:
    assert _at(in_minutes=20) == NOW + timedelta(minutes=20)


def test_a_time_said_without_a_day_that_has_passed_today_means_tomorrow() -> None:
    assert _at(hour=9, ampm="am") == datetime(2026, 10, 20, 9, tzinfo=TZ)


def test_a_time_already_gone_today_is_asked_about() -> None:
    gone = resolve(_set(day="today", hour=9, ampm="am"), NOW, TZ)
    assert gone.at is None
    assert "passed" in gone.unclear


def test_weekdays_are_the_next_one_and_next_weekday_is_asked() -> None:
    assert _at(day="weekday", weekday="friday", hour=6, ampm="pm") == datetime(
        2026, 10, 23, 18, tzinfo=TZ
    )
    assert _at(day="weekday", weekday="monday", hour=6, ampm="pm") == datetime(
        2026, 10, 26, 18, tzinfo=TZ
    )  # "monday" said on a Monday is the next one
    nxt = resolve(_set(day="weekday", weekday="friday", next_said=True, hour=6), NOW, TZ)
    assert nxt.at is None
    assert "this friday or the one after" in nxt.unclear


def test_a_vague_check_in_lands_at_a_picked_time_in_the_window_and_says_only_the_part() -> None:
    times = {
        resolve(_set(kind="check_in", day="in_days"), NOW, TZ, Random(n)).at for n in range(40)
    }
    assert all(t is not None and t.date() == date(2026, 10, 22) for t in times)
    assert all(
        t is not None and time(16) <= t.time() <= time(20) and t.minute % 5 == 0 for t in times
    )
    assert len(times) > 10  # picked, not fixed
    when = resolve(_set(kind="check_in", day="in_days"), NOW, TZ, Random(1))
    assert when.defaulted
    assert when.loose
    assert when.at is not None
    part = "afternoon" if when.at.hour < 17 else "evening"
    assert spoken(when.at, NOW, TZ, loose=True) == f"Thursday {part}"
    assert not resolve(_set(hour=8, ampm="pm"), NOW, TZ).loose
    assert not resolve(_set(kind="check_in", day="tomorrow", part="morning"), NOW, TZ).loose


def test_a_check_in_later_today_is_at_least_half_an_hour_off_or_moves_to_tomorrow() -> None:
    late_afternoon = datetime(2026, 10, 19, 17, 0, tzinfo=TZ)
    for n in range(20):
        at = resolve(_set(kind="check_in"), late_afternoon, TZ, Random(n)).at
        assert at is not None
        assert late_afternoon + timedelta(minutes=30) <= at <= datetime(2026, 10, 19, 20, tzinfo=TZ)
    night = datetime(2026, 10, 19, 21, 0, tzinfo=TZ)
    at = resolve(_set(kind="check_in"), night, TZ, Random(0)).at
    assert at is not None
    assert at.date() == date(2026, 10, 20)
    assert resolve(_set(kind="check_in", day="today"), night, TZ, Random(0)).at is None


def test_a_reminder_with_no_time_at_all_is_asked_about() -> None:
    assert resolve(_set(day="tomorrow"), NOW, TZ).unclear == "what time"


def test_further_than_sixty_days_is_asked_about() -> None:
    far = resolve(_set(day="in_days", days=90, hour=9, ampm="am"), NOW, TZ)
    assert far.at is None
    assert "sixty days" in far.unclear


def test_the_wall_clock_holds_across_a_clock_change() -> None:
    at = _at(day="date", on_date="2026-11-02", hour=9, ampm="am")
    assert at is not None
    assert at.astimezone(UTC).time() == time(14)  # 9 am after the clocks went back is 14:00 UTC
    assert _at(day="date", on_date="the 2nd") is None


def test_spoken_says_the_time_as_a_person_would() -> None:
    assert spoken(datetime(2026, 10, 19, 20, tzinfo=TZ), NOW, TZ) == "tonight at 8:00 pm"
    assert spoken(datetime(2026, 10, 20, 9, tzinfo=TZ), NOW, TZ) == "tomorrow at 9:00 am"
    assert spoken(datetime(2026, 10, 23, 18, tzinfo=TZ), NOW, TZ) == "Friday 23 Oct at 6:00 pm"


def test_parse_takes_a_full_answer_and_refuses_a_broken_one() -> None:
    s = parse(
        {
            "ask": "set",
            "kind": "reminder",
            "thing": " take the dog out ",
            "day": "today",
            "hour": 8,
            "ampm": "pm",
            "part": "unsaid",
            "repeats": False,
        }
    )
    assert s is not None
    assert (s.thing, s.hour, s.ampm, s.minute) == ("take the dog out", 8, "pm", 0)
    assert parse({"ask": "maybe", "kind": "reminder", "thing": "x"}) is None
    assert parse(["set"]) is None


def test_only_messages_with_reminder_words_or_an_answer_to_when_are_read() -> None:
    assert likely("remind me at 8 to take the dog out", asked_when=False)
    assert likely("can you check up on me in a few days", asked_when=False)
    assert not likely("i'll remember, dont worry", asked_when=False)
    assert likely("evening", asked_when=True)
    assert likely("can you tell me good morning every day?", asked_when=False)
    assert likely("say goodnight to me every night", asked_when=False)
    assert likely("you can stop saying good morning", asked_when=False)
    assert not likely("good morning!!", asked_when=False)


def test_a_cancel_drops_the_one_it_names_or_the_only_one() -> None:
    pending = [("a", "take the dog out"), ("b", "call mum")]
    assert matching(pending, "the dog thing") == ["a"]
    assert matching(pending, "that") == []
    assert matching([("a", "take the dog out")], "that") == ["a"]


def test_hour_zero_is_midnight_only_when_they_say_so() -> None:
    from companion.features.reminders.logic import Ask, Kind, Slots, trusted  # noqa: PLC0415

    placeholder = Slots(Ask.SET, Kind.REMINDER, "take the dog out", hour=0, part="evening")
    assert trusted(placeholder, "remind me this evening to take the dog out").hour is None
    assert trusted(placeholder, "remind me at midnight to take the dog out").hour == 0
    assert trusted(placeholder, "remind me at 12am").hour == 0
