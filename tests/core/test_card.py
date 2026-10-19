from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from companion.core.card import HOLD_AT, build_card, render
from companion.core.types import Belief, BeliefKind
from tests.conftest import T0

NOW = T0 + timedelta(days=2)


def _b(belief: Callable[..., Belief], bid: str, claim: str, **over: object) -> Belief:
    return belief(bid=bid, claim=claim, **over)


def _card(beliefs: list[Belief], now: datetime = NOW, support: dict[str, datetime] | None = None):
    return build_card(beliefs, support or {}, now)  # type: ignore[arg-type]


def test_sensitive_beliefs_are_held_not_surfaced(belief: Callable[..., Belief]) -> None:
    card = _card(
        [
            _b(belief, "a", "Likes climbing", sensitivity=0),
            _b(belief, "b", "Has OCD", sensitivity=2),
        ]
    )
    assert [b.claim for b in card.usable] == ["Likes climbing"]
    assert [b.claim for b in card.held] == ["Has OCD"]
    assert HOLD_AT == 2


def test_the_rendering_separates_the_lists_and_never_leaks_held_into_usable(
    belief: Callable[..., Belief],
) -> None:
    text = render(
        _card([_b(belief, "a", "Likes climbing"), _b(belief, "b", "Has OCD", sensitivity=3)])
    )
    usable, held = text.split("[Also known")
    assert "Likes climbing" in usable
    assert "Has OCD" not in usable
    assert "Has OCD" in held


def test_an_empty_card_renders_nothing() -> None:
    card = _card([])
    assert card.empty
    assert render(card) == ""


def test_boundaries_come_first_and_the_card_is_capped(belief: Callable[..., Belief]) -> None:
    many = [
        _b(belief, f"p{i}", f"pref {i}", kind=BeliefKind.PREFERENCE, valid_from=T0 + timedelta(i))
        for i in range(20)
    ]
    boundary = _b(belief, "bd", "Wants fewer questions", kind=BeliefKind.BOUNDARY)
    card = build_card([*many, boundary], {}, NOW + timedelta(days=30), max_items=5)
    assert len(card.usable) == 5
    assert card.usable[0].claim == "Wants fewer questions"


def test_each_line_says_how_long_ago_it_was_mentioned(belief: Callable[..., Belief]) -> None:
    text = render(_card([_b(belief, "a", "Likes climbing")]))
    assert "Likes climbing (mentioned 2 days ago)" in text


def test_an_aging_state_says_it_may_have_changed(belief: Callable[..., Belief]) -> None:
    b = _b(belief, "a", "Feels lonely", kind=BeliefKind.STATE)
    text = render(_card([b], now=T0 + timedelta(days=10)))
    assert "Feels lonely (mentioned 10 days ago; may have changed)" in text


def test_a_stale_state_leaves_the_main_card_and_goes_to_the_older_block(
    belief: Callable[..., Belief],
) -> None:
    b = _b(belief, "a", "Feels lonely", kind=BeliefKind.STATE, sensitivity=0)
    card = _card([b], now=T0 + timedelta(days=40))
    assert card.usable == ()
    assert [x.claim for x in card.older] == ["Feels lonely"]
    text = render(card)
    assert text.startswith("[Older, and may be out of date")
    assert "Feels lonely" in text


def test_a_stale_sensitive_state_is_left_out_entirely(belief: Callable[..., Belief]) -> None:
    b = _b(belief, "a", "Feels lonely", kind=BeliefKind.STATE, sensitivity=2)
    card = _card([b], now=T0 + timedelta(days=40))
    assert (card.usable, card.held, card.older) == ((), (), ())
    assert [x.id for x in card.dropped] == ["a"]
    assert render(card) == ""
    assert card.empty


def test_the_older_block_is_capped_and_keeps_the_most_recent(
    belief: Callable[..., Belief],
) -> None:
    states = [
        _b(belief, f"s{i}", f"state {i}", kind=BeliefKind.STATE, valid_from=T0 + timedelta(hours=i))
        for i in range(5)
    ]
    card = _card(states, now=T0 + timedelta(days=60))
    assert [b.id for b in card.older] == ["s4", "s3", "s2"]
    assert {b.id for b in card.dropped} == {"s0", "s1"}


def test_restating_a_belief_keeps_it_fresh(belief: Callable[..., Belief]) -> None:
    b = _b(belief, "a", "Feels lonely", kind=BeliefKind.STATE)
    now = T0 + timedelta(days=40)
    assert _card([b], now=now).usable == ()
    refreshed = _card([b], now=now, support={"a": now - timedelta(days=1)})
    assert [x.id for x in refreshed.usable] == ["a"]
    assert "mentioned yesterday" in render(refreshed)


def test_an_event_never_goes_stale(belief: Callable[..., Belief]) -> None:
    b = _b(belief, "a", "Started the project on 2026-10-14", kind=BeliefKind.EVENT)
    card = _card([b], now=T0 + timedelta(days=900))
    assert [x.id for x in card.usable] == ["a"]


def test_what_does_not_fit_on_the_card_is_kept_as_crowded_out(
    belief: Callable[..., Belief],
) -> None:
    many = [
        _b(belief, f"p{i}", f"pref {i}", kind=BeliefKind.PREFERENCE, valid_from=T0 + timedelta(i))
        for i in range(8)
    ]
    card = build_card(many, {}, NOW + timedelta(days=9), max_items=5)
    assert len(card.usable) == 5
    assert len(card.crowded) == 3
    assert not set(card.crowded) & set(card.usable)
