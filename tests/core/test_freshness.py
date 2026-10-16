from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from companion.core.freshness import HORIZON_DAYS, Freshness, status, when_phrase
from companion.core.types import BeliefKind
from tests.conftest import T0


def test_every_kind_has_a_horizon() -> None:
    assert set(HORIZON_DAYS) == set(BeliefKind)


@pytest.mark.parametrize(
    ("kind", "days", "expected"),
    [
        (BeliefKind.STATE, 0, Freshness.FRESH),
        (BeliefKind.STATE, 7, Freshness.FRESH),
        (BeliefKind.STATE, 8, Freshness.AGING),
        (BeliefKind.STATE, 14, Freshness.AGING),
        (BeliefKind.STATE, 15, Freshness.STALE),
        (BeliefKind.THREAD, 31, Freshness.STALE),
        (BeliefKind.TRAIT, 200, Freshness.AGING),
        (BeliefKind.TRAIT, 400, Freshness.STALE),
        (BeliefKind.EVENT, 5000, Freshness.FRESH),
    ],
)
def test_status_by_kind_and_age(kind: BeliefKind, days: int, expected: Freshness) -> None:
    assert status(kind, T0, T0 + timedelta(days=days)) is expected


@pytest.mark.parametrize(
    ("days", "text"),
    [
        (0, "today"),
        (1, "yesterday"),
        (5, "5 days ago"),
        (13, "13 days ago"),
        (21, "3 weeks ago"),
        (59, "8 weeks ago"),
        (90, "3 months ago"),
    ],
)
def test_when_phrase_counts_the_users_calendar_days(days: int, text: str) -> None:
    now = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
    assert when_phrase(now - timedelta(days=days), now, UTC) == text


def test_something_said_last_evening_is_yesterday_even_if_under_24_hours_ago() -> None:
    now = datetime(2026, 10, 16, 16, 51, tzinfo=UTC)
    last_evening = datetime(2026, 10, 15, 21, 0, tzinfo=UTC)  # 20 hours earlier
    assert when_phrase(last_evening, now, UTC) == "yesterday"


def test_something_said_this_morning_is_today_however_late_it_is() -> None:
    now = datetime(2026, 10, 16, 23, 30, tzinfo=UTC)
    assert when_phrase(datetime(2026, 10, 16, 0, 5, tzinfo=UTC), now, UTC) == "today"


def test_the_day_is_the_users_not_utc() -> None:
    new_york = timezone(timedelta(hours=-4))
    now = datetime(2026, 10, 16, 3, 0, tzinfo=UTC)  # 23:00 on the 15th in New York
    said = datetime(2026, 10, 15, 22, 0, tzinfo=UTC)  # 18:00 on the 15th in New York
    assert when_phrase(said, now, new_york) == "today"


def test_a_future_timestamp_is_treated_as_today() -> None:
    now = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)
    assert when_phrase(now + timedelta(days=3), now, UTC) == "today"
