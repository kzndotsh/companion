from __future__ import annotations

import pytest

from companion.core.length import FLOOR_WORDS, MAX_USER_WORDS, length_note, reply_limit


def test_a_short_statement_gets_a_note_with_a_limit_near_what_they_wrote() -> None:
    note = length_note("just got home")
    assert note is not None
    assert "3 words" in note
    assert f"under about {reply_limit(3)} words" in note
    assert "unless what they said needs more" in note


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
def test_questions_long_messages_and_nothing_get_no_note(text: str) -> None:
    assert length_note(text) is None


def test_the_limit_grows_with_what_they_wrote_and_never_drops_below_the_floor() -> None:
    assert reply_limit(1) == FLOOR_WORDS
    assert reply_limit(4) < reply_limit(8) < reply_limit(12)
    assert reply_limit(MAX_USER_WORDS) < 2 * MAX_USER_WORDS + 5


def test_the_longest_message_that_still_counts_as_short_gets_a_note() -> None:
    assert length_note(" ".join(["word"] * MAX_USER_WORDS)) is not None


def test_a_serious_message_gets_no_length_note_however_short() -> None:
    assert length_note("i want to die", serious=True) is None
    assert length_note("i want to die") is not None
