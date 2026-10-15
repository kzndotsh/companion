from __future__ import annotations

from datetime import timedelta

import pytest

from companion.core.freshness import HORIZON_DAYS, Freshness, age_phrase, status
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
def test_age_phrase(days: int, text: str) -> None:
    assert age_phrase(timedelta(days=days)) == text


def test_a_future_timestamp_is_treated_as_today() -> None:
    assert age_phrase(timedelta(days=-3)) == "today"
