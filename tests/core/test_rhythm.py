from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from companion.core.rhythm import kept_hour, learn

NOW = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)


def _spaced(n: int, hours: float) -> list[datetime]:
    """n single-message conversations, `hours` apart, the last one hour before NOW."""
    last = NOW - timedelta(hours=1)
    return [last - timedelta(hours=hours * i) for i in range(n)]


def test_with_no_history_it_is_the_baseline() -> None:
    r = learn([], NOW, UTC)
    assert (r.conversations, r.weight, r.learned_pause, r.pause) == (0, 0.0, None, 12.0)
    assert r.usual == frozenset(range(9, 22))
    assert r.quiet == frozenset({23, 0, 1, 2, 3, 4, 5, 6, 7})


@pytest.mark.parametrize(
    ("n", "weight", "pause"),
    [(1, 0.05, 12.0), (10, 0.5, 13.5), (20, 1.0, 15.0), (22, 1.0, 15.0)],
)
def test_their_pause_counts_more_the_more_conversations_it_has_seen(
    n: int, weight: float, pause: float
) -> None:
    r = learn(_spaced(n, 15), NOW, UTC)
    assert r.conversations == n
    assert r.weight == pytest.approx(weight)
    assert r.pause == pytest.approx(pause)


def test_missing_them_is_never_under_eight_hours() -> None:
    r = learn(_spaced(30, 3), NOW, UTC)
    assert r.learned_pause == pytest.approx(3.0)
    assert r.pause == 8.0


def test_only_the_last_two_weeks_count() -> None:
    old = [NOW - timedelta(days=20, hours=i) for i in range(0, 60, 3)]
    assert learn(old, NOW, UTC).conversations == 0


def test_a_night_shift_learns_quiet_hours_in_the_day() -> None:
    nights = [
        datetime(2026, 10, day, hour, 15, tzinfo=UTC) + timedelta(days=offset)
        for day in range(6, 19)
        for hour, offset in ((22, 0), (0, 1), (3, 1), (5, 1))
    ]
    r = learn(nights, NOW, UTC)
    assert r.weight == 1.0
    assert {12, 14, 16} <= r.quiet
    assert not {22, 0, 3, 5} & r.quiet
    assert {0, 3} <= r.usual
    assert 12 not in r.usual


def test_a_time_they_keep_is_the_same_hour_on_most_of_the_last_week() -> None:
    mornings = [datetime(2026, 10, d, 7, 40, tzinfo=UTC) for d in (13, 14, 15, 17, 19)]
    assert kept_hour(mornings, NOW, UTC) == 7
    assert kept_hour(mornings[:4], NOW, UTC) is None
    today = [datetime(2026, 10, 20, 7, m, tzinfo=UTC) for m in range(5)]
    assert kept_hour(mornings[:4] + today, NOW, UTC) is None  # today is not part of the habit


def test_a_night_hour_is_quiet_unless_they_start_conversations_in_it() -> None:
    tz = UTC
    now = datetime(2026, 10, 30, 15, 0, tzinfo=tz)

    def night(day: int, hour: int) -> list[datetime]:
        start = datetime(2026, 10, 16 + day, hour, 0, tzinfo=tz)
        return [start + timedelta(minutes=30 * i) for i in range((26 - hour) % 24 * 2)]

    noons = [datetime(2026, 10, 16 + d, 12, 0, tzinfo=tz) for d in range(13)]
    # Every day a chat starts at 10 PM and runs on to 2 AM: they write at 1 AM but never start then.
    late = noons + [t for d in range(13) for t in night(d, 22)]
    assert 1 in learn(late, now, tz).quiet
    # Three nights they skip the evening and start at 1 AM instead: the hour is theirs.
    evenings = [t for d in range(13) if d not in (1, 4, 7) for t in night(d, 22)]
    owned = noons + evenings + [t for d in (2, 5, 8) for t in night(d, 1)]
    assert 1 not in learn(owned, now, tz).quiet
