"""A table keyed by memory kind must name every kind: a new kind with no row fails here, not as a
KeyError in the middle of a turn."""

from companion.core.card import KIND_ORDER
from companion.core.freshness import HORIZON_DAYS
from companion.core.types import BeliefKind


def test_every_kind_has_a_freshness_horizon() -> None:
    assert set(HORIZON_DAYS) == set(BeliefKind)


def test_every_kind_has_a_place_in_the_card_order() -> None:
    assert set(KIND_ORDER) == set(BeliefKind)
