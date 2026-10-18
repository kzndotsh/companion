from __future__ import annotations

import pytest

from companion.core.length import (
    FLOOR_WORDS,
    MAX_USER_WORDS,
    MIN_VARIED_WORDS,
    SERIOUS_WORDS,
    VARY,
    length_target,
    reply_limit,
)


def test_a_short_statement_gets_a_note_with_a_limit_near_what_they_wrote() -> None:
    size = length_target("just got home")
    assert size is not None
    assert size.words == reply_limit(3)
    assert "3 words" in size.note
    assert f"under about {reply_limit(3)} words" in size.note
    assert "unless what they said needs more" in size.note
    assert "short statement of 3 words" in size.why


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "what should i make for dinner?",
        "wait, really? okay",
        " ".join(["word"] * (MAX_USER_WORDS + 1)),
    ],
)
def test_questions_long_messages_and_nothing_get_no_target(text: str) -> None:
    assert length_target(text) is None


def test_the_limit_grows_with_what_they_wrote_and_never_drops_below_the_floor() -> None:
    assert reply_limit(1) == FLOOR_WORDS
    assert reply_limit(4) < reply_limit(8) < reply_limit(12)
    assert reply_limit(MAX_USER_WORDS) < 2 * MAX_USER_WORDS + 5


def test_the_longest_message_that_still_counts_as_short_gets_a_target() -> None:
    assert length_target(" ".join(["word"] * MAX_USER_WORDS)) is not None


def test_a_serious_message_gets_the_serious_target_and_an_acute_one_none() -> None:
    serious = length_target("i want to die", severity=2)
    assert serious is not None
    assert serious.words == SERIOUS_WORDS
    assert f"under about {SERIOUS_WORDS} words" in serious.note
    assert "Their message was short" not in serious.note
    assert length_target("i want to die", severity=3) is None
    assert length_target("long serious story " * 10, severity=2) is not None


def test_a_scene_gets_no_target() -> None:
    assert length_target("just got home", in_scene=True) is None


def test_the_target_varies_by_turn_within_bounds_and_repeats_for_the_same_turn() -> None:
    base = reply_limit(4)
    words = [length_target("got a haircut today", seed=f"turn-{i}") for i in range(200)]
    sizes = [w.words for w in words if w is not None]
    assert len(sizes) == 200
    assert len(set(sizes)) > 3
    assert min(sizes) >= max(MIN_VARIED_WORDS, round(base * VARY[0]) - 1)
    assert max(sizes) <= round(base * VARY[1]) + 1
    first = length_target("got a haircut today", seed="turn-7")
    again = length_target("got a haircut today", seed="turn-7")
    assert first == again
