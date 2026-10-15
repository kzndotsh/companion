from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from companion.core.card import HOLD_AT, build_card, render
from companion.core.types import Belief, BeliefKind
from tests.conftest import T0


def _b(belief: Callable[..., Belief], bid: str, claim: str, **over: object) -> Belief:
    return belief(bid=bid, claim=claim, **over)


def test_sensitive_beliefs_are_held_not_surfaced(belief: Callable[..., Belief]) -> None:
    card = build_card(
        [
            _b(belief, "a", "Likes climbing", sensitivity=0),
            _b(belief, "b", "Has OCD", sensitivity=2),
        ]
    )
    assert [b.claim for b in card.usable] == ["Likes climbing"]
    assert [b.claim for b in card.held] == ["Has OCD"]
    assert HOLD_AT == 2


def test_the_rendering_separates_the_two_lists_and_never_leaks_held_into_usable(
    belief: Callable[..., Belief],
) -> None:
    text = render(
        build_card([_b(belief, "a", "Likes climbing"), _b(belief, "b", "Has OCD", sensitivity=3)])
    )
    usable, held = text.split("[Also known")
    assert "Likes climbing" in usable
    assert "Has OCD" not in usable
    assert "Has OCD" in held


def test_an_empty_card_renders_nothing() -> None:
    card = build_card([])
    assert card.empty
    assert render(card) == ""


def test_boundaries_come_first_and_the_card_is_capped(belief: Callable[..., Belief]) -> None:
    many = [
        _b(belief, f"p{i}", f"pref {i}", kind=BeliefKind.PREFERENCE, valid_from=T0 + timedelta(i))
        for i in range(20)
    ]
    boundary = _b(belief, "bd", "Wants fewer questions", kind=BeliefKind.BOUNDARY)
    card = build_card([*many, boundary], max_items=5)
    assert len(card.usable) == 5
    assert card.usable[0].claim == "Wants fewer questions"
