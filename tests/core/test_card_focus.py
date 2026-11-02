from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from companion.core.card import FOCUS_HELD, FOCUS_PERSONAL, Focus, build_card
from companion.core.types import Belief, BeliefId, BeliefKind
from companion.core.vectors import unit
from tests.conftest import T0

NOW = T0 + timedelta(days=2)


def _focus(near: dict[str, float], axes: dict[str, list[float]] | None = None) -> Focus:
    """Each memory on its own axis unless `axes` puts two on the same one."""
    names = sorted(near)
    vectors = {
        BeliefId(n): unit(
            (axes or {}).get(n) or [1.0 if i == j else 0.0 for j in range(len(names))]
        )
        for i, n in enumerate(names)
    }
    return Focus({BeliefId(n): s for n, s in near.items()}, vectors)


def _claims(card_part: tuple[Belief, ...]) -> list[str]:
    return [b.claim for b in card_part]


def test_after_the_rules_the_closest_memories_come_first(belief: Callable[..., Belief]) -> None:
    beliefs = [
        belief(bid="rule", claim="No medical advice", kind=BeliefKind.BOUNDARY),
        belief(bid="film", claim="Watches one film every winter", kind=BeliefKind.TRAIT),
        belief(bid="coffee", claim="Drinks coffee late", kind=BeliefKind.PREFERENCE),
    ]
    focus = _focus({"film": 0.1, "coffee": 0.6})
    card = build_card(beliefs, {}, NOW, focus=focus)
    assert _claims(card.usable) == [
        "No medical advice",
        "Drinks coffee late",
        "Watches one film every winter",
    ]


def test_a_full_card_leaves_the_far_ones_crowded_out(belief: Callable[..., Belief]) -> None:
    beliefs = [belief(bid=f"m{i}", claim=f"memory {i}") for i in range(4)]
    card = build_card(
        beliefs, {}, NOW, max_items=2, focus=_focus({f"m{i}": i / 10 for i in range(4)})
    )
    assert _claims(card.usable) == ["memory 3", "memory 2"]
    assert sorted(_claims(card.crowded)) == ["memory 0", "memory 1"]


def test_a_memory_that_says_what_one_already_chosen_says_is_skipped(
    belief: Callable[..., Belief],
) -> None:
    beliefs = [
        belief(bid="a", claim="Likes the holiday film"),
        belief(bid="b", claim="Names the holiday film as a favourite"),
        belief(bid="c", claim="Has two dogs"),
    ]
    focus = _focus({"a": 0.6, "b": 0.5, "c": 0.2}, {"a": [1, 0], "b": [1, 0.05], "c": [0, 1]})
    card = build_card(beliefs, {}, NOW, focus=focus)
    assert _claims(card.usable) == ["Likes the holiday film", "Has two dogs"]


def test_a_held_memory_needs_them_sharing_and_a_close_match(belief: Callable[..., Belief]) -> None:
    beliefs = [belief(bid="h", claim="Takes a medication", sensitivity=2)]
    near = _focus({"h": FOCUS_HELD + 0.05})
    far = _focus({"h": FOCUS_HELD - 0.05})
    assert _claims(build_card(beliefs, {}, NOW, show_held=True, focus=near).held) == [
        "Takes a medication"
    ]
    assert not build_card(beliefs, {}, NOW, show_held=True, focus=far).held
    assert not build_card(beliefs, {}, NOW, show_held=False, focus=near).held


def test_a_mildly_personal_memory_needs_a_close_match(belief: Callable[..., Belief]) -> None:
    beliefs = [belief(bid="p", claim="Had a hard breakup", sensitivity=1)]
    assert build_card(beliefs, {}, NOW, focus=_focus({"p": FOCUS_PERSONAL + 0.01})).usable
    assert not build_card(beliefs, {}, NOW, focus=_focus({"p": FOCUS_PERSONAL - 0.01})).usable


def test_a_memory_with_no_vector_is_not_ranked(belief: Callable[..., Belief]) -> None:
    beliefs = [
        belief(bid="new", claim="Said this a moment ago"),
        belief(bid="old", claim="Old one"),
    ]
    card = build_card(beliefs, {}, NOW, focus=_focus({"old": 0.3}))
    assert _claims(card.usable) == ["Old one"]
    assert _claims(card.crowded) == ["Said this a moment ago"]
