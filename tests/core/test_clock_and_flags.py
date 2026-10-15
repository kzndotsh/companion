from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from companion.core.clock import describe_gap, volatile_line
from companion.core.flags import parse_flag
from companion.core.types import FlagKind

NOW = datetime(2026, 10, 15, 16, 54, tzinfo=UTC)


@pytest.mark.parametrize(
    ("gap", "expected"),
    [
        (timedelta(seconds=59), None),
        (timedelta(minutes=1), "1 minute"),
        (timedelta(minutes=10), "10 minutes"),
        (timedelta(minutes=59), "59 minutes"),
        (timedelta(hours=1), "1 hour"),
        (timedelta(hours=23), "23 hours"),
        (timedelta(days=1), "1 day"),
        (timedelta(days=13), "13 days"),
        (timedelta(days=21), "3 weeks"),
    ],
)
def test_describe_gap(gap: timedelta, expected: str | None) -> None:
    assert describe_gap(gap) == expected


def test_volatile_line_has_no_gap_when_continuous() -> None:
    assert "last message" not in volatile_line(NOW, NOW - timedelta(seconds=30))
    assert "last message" not in volatile_line(NOW, None)


def test_volatile_line_names_a_long_gap() -> None:
    assert "last message 3 hours ago" in volatile_line(NOW, NOW - timedelta(hours=3))


@pytest.mark.parametrize(
    ("arg", "kind", "note"),
    [
        ("forgot you knew I'm building you", FlagKind.FORGOT, "you knew I'm building you"),
        ("FORGOT", FlagKind.FORGOT, ""),
        ("too_much and too long", FlagKind.TOO_MUCH, "and too long"),
        ("unwanted", FlagKind.UNWANTED, ""),
        ("that was weird", FlagKind.OFF, "that was weird"),
        ("", FlagKind.OFF, ""),
    ],
)
def test_parse_flag(arg: str, kind: FlagKind, note: str) -> None:
    assert parse_flag(arg) == (kind, note)
