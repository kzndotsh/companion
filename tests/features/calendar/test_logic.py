from __future__ import annotations

from datetime import date, timedelta

import pytest

from companion.features.calendar.logic import (
    REGION,
    Dated,
    How,
    Kind,
    Occasion,
    add_months,
    fallback_days,
    note,
    occasions,
    pick,
    their_dates,
    together,
    yearly,
)


def _on_the_day(day: date) -> dict[str, Kind]:
    return {o.name: o.kind for o in occasions(day, REGION, None) if o.how is How.ON_THE_DAY}


def test_the_library_gives_halloween_as_cultural_and_the_big_public_days() -> None:
    assert _on_the_day(date(2026, 10, 31)) == {"Halloween": Kind.CULTURAL}
    assert _on_the_day(date(2026, 11, 26)) == {"Thanksgiving": Kind.PUBLIC}
    assert _on_the_day(date(2026, 12, 25)) == {"Christmas Day": Kind.PUBLIC}
    assert _on_the_day(date(2026, 7, 3)) == {}  # an observed stand-in is not the day
    assert not occasions(date(2026, 10, 20), REGION, None)


def test_the_days_written_in_code_fall_where_the_library_puts_them() -> None:
    for year in (2026, 2027):
        for name, day in fallback_days(year).items():
            assert name in _on_the_day(day), (name, day)


@pytest.mark.parametrize(("year", "last"), [(2026, 28), (2028, 29)])
def test_a_month_from_the_31st_of_january_lands_on_februarys_last_day(year: int, last: int) -> None:
    first = date(year, 1, 31)
    assert add_months(first, 1) == date(year, 2, last)
    assert together(date(year, 2, last), first) == "a month"
    assert together(date(year, 2, last - 1), first) is None


def test_the_relationships_dates() -> None:
    first = date(2026, 3, 10)
    assert together(first + timedelta(days=100), first) == "a hundred days"
    assert together(date(2026, 9, 10), first) == "six months"
    assert together(date(2027, 3, 10), first) == "a year"
    assert together(date(2029, 3, 10), first) == "three years"
    assert together(first, first) is None
    assert together(date(2029, 2, 28), date(2028, 2, 29)) == "a year"


def test_a_big_day_has_one_lead_up_and_a_small_one_none() -> None:
    [two] = [o for o in occasions(date(2026, 10, 29), REGION, None) if o.how is How.LEAD_UP]
    [one] = [o for o in occasions(date(2026, 10, 30), REGION, None) if o.how is How.LEAD_UP]
    assert note(two, date(2026, 10, 29)).startswith("[Halloween is in two days.")
    assert note(one, date(2026, 10, 30)).startswith("[Halloween is tomorrow.")
    assert two.key == one.key  # offered once in total, not on both days
    assert pick([one], {two.key}) is None
    assert not occasions(date(2026, 11, 9), REGION, None)  # Veterans Day has no lead-up


def test_the_order_is_the_relationship_then_the_day_then_a_lead_up_and_each_once() -> None:
    today = date(2026, 12, 24)
    found = occasions(today, REGION, date(2026, 11, 24))
    offered: set[str] = set()
    picked: list[Occasion] = []
    while (o := pick(found, offered)) is not None:
        picked.append(o)
        offered.add(o.key)
    assert [(o.name, o.kind, o.how) for o in picked] == [
        ("a month", Kind.RELATIONSHIP, How.ON_THE_DAY),
        ("Christmas Eve", Kind.CULTURAL, How.ON_THE_DAY),
        ("Christmas Day", Kind.PUBLIC, How.LEAD_UP),
    ]
    assert note(picked[0], today).startswith("[Today it has been a month since the two of you")
    assert note(picked[1], today).startswith("[Today is Christmas Eve. Mention it lightly")


def test_days_of_remembrance_and_contested_days_are_left_out() -> None:
    from companion.features.calendar.logic import LEFT_OUT, occasions  # noqa: PLC0415

    year = [
        o.name
        for d in range(365)
        for o in occasions(date(2026, 1, 1) + timedelta(days=d), "US", None)
    ]
    assert not set(year) & LEFT_OUT
    assert "Halloween" in year


@pytest.mark.parametrize(
    ("claim", "want"),
    [
        (
            "The user turns 30 on December 4th (their birthday is December 4).",
            ("their birthday", 12, 4),
        ),
        ("The user's sister's birthday is on the 3rd of March.", ("their sister's birthday", 3, 3)),
        (
            "The user and their partner have an anniversary on June 12.",
            ("their anniversary", 6, 12),
        ),
        ("Their birthday is Sept. 9th", ("their birthday", 9, 9)),
        ("The anniversary of their dad dying is May 2.", None),
        ("Their mom passed on April 9; the anniversary is hard.", None),
        ("The user started a new job on March 3.", None),
        ("On 2026-10-24 the user had chicken for dinner.", None),
        ("Their birthday is February 31.", None),
    ],
)
def test_a_yearly_date_is_read_from_a_memory_and_a_hard_one_never(
    claim: str, want: tuple[str, int, int] | None
) -> None:
    assert yearly(claim) == (Dated(*want) if want else None)


def test_their_dates_skip_a_sensitive_memory_and_come_once() -> None:
    birthday = "Their birthday is December 4."
    found = their_dates([(birthday, 0), (birthday, 1), ("Their anniversary is June 12.", 2)])
    assert found == (Dated("their birthday", 12, 4),)
    assert Dated("their birthday", 2, 29).on(2027) == date(2027, 2, 28)


def test_their_own_date_comes_first_and_has_a_lead_up() -> None:
    birthday = Dated("their birthday", 11, 15)
    day = occasions(date(2026, 11, 15), REGION, date(2026, 10, 15), [birthday])
    assert [(o.name, o.kind) for o in day][:2] == [
        ("their birthday", Kind.THEIRS),
        ("a month", Kind.RELATIONSHIP),
    ]
    first = pick(day, set())
    assert first is not None
    assert first.kind is Kind.THEIRS
    assert note(first, date(2026, 11, 15)).startswith("[Today is their birthday. Mark it warmly")
    soon = pick(occasions(date(2026, 11, 13), REGION, None, [birthday]), set())
    assert soon is not None
    assert (soon.how, soon.kind) == (How.LEAD_UP, Kind.THEIRS)
    assert note(soon, date(2026, 11, 13)).startswith("[Their birthday is in two days.")
