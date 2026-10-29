from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from companion.core.card import build_card, render
from companion.core.quoted import wants_context
from companion.core.types import Belief, BeliefKind
from companion.features.upkeep.context.logic import parse
from tests.conftest import T0


def test_only_feelings_and_sensitive_memories_want_a_note(belief: Callable[..., Belief]) -> None:
    assert wants_context(belief(kind=BeliefKind.STATE))
    assert wants_context(belief(kind=BeliefKind.PREFERENCE, sensitivity=2))
    assert not wants_context(belief(kind=BeliefKind.PREFERENCE, sensitivity=1))
    assert not wants_context(belief(kind=BeliefKind.EVENT))


def test_a_note_is_a_short_clause() -> None:
    assert parse({"context": "  While venting about work. "}) == "while venting about work"
    assert parse({"context": "word " * 30}) is None
    assert parse({"context": ""}) is None
    assert parse(["x"]) is None


def test_the_card_shows_the_note_only_beside_a_memory_that_wants_one(
    belief: Callable[..., Belief],
) -> None:
    sad = belief(bid="sad", kind=BeliefKind.STATE, claim="Feels low.")
    tea = belief(bid="tea", kind=BeliefKind.PREFERENCE, claim="Likes tea.")
    notes = {sad.id: "while talking about a long week", tea.id: "while making tea"}
    card = build_card([sad, tea], {}, T0 + timedelta(hours=1), contexts=notes)
    text = render(card)
    assert "Feels low. (mentioned today; said while talking about a long week)" in text
    assert "Likes tea. (mentioned today)" in text
