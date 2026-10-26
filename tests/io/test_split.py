from __future__ import annotations

import pytest

from companion.io.split import (
    MIN_PART_WORDS,
    SPLIT_CHANCE,
    eligible,
    fit,
    sentences,
    split_reply,
)

TWO = (
    "A lot of it is learned association: the smell is tied to waking up, comfort, and that first "
    "quiet moment of the day. Plus the aroma itself is rich and complex, so your brain gets a "
    "little reward before you even drink it."
)
THREE = (
    "yeah i know. but i'm gonna keep it straight anyway, because i can't do the physical stuff "
    "and pretending otherwise would just be annoying for both of us, honestly. go get food for "
    "real though."
)
LONG = " ".join(
    f"This is sentence number {n} and it has a handful of words in it." for n in range(8)
)


def test_the_pieces_are_the_same_words_in_the_same_order() -> None:
    for text in (TWO, THREE, LONG):
        parts = split_reply(text, 0.0, 0.0)
        assert len(parts) >= 2
        assert " ".join(parts) == text


def test_a_roll_at_or_over_the_chance_sends_one_message() -> None:
    assert split_reply(TWO, SPLIT_CHANCE, 0.0) == [TWO]
    assert split_reply(TWO, 0.99, 0.0) == [TWO]
    assert len(split_reply(TWO, SPLIT_CHANCE - 0.01, 0.0)) == 2


@pytest.mark.parametrize(
    "text",
    [
        "short reply, only a few words. second sentence.",
        "one long sentence with no end punctuation inside it " * 4,
        "*tilts my head* " + TWO,
        "I lean closer and keep my voice low. " + TWO + ' "stay right there for me."',
        TWO + "\n\nA second paragraph that is already structured on its own line.",
        "- one thing to try here and there and everywhere\n- another thing to try " + TWO,
    ],
)
def test_replies_that_should_stay_whole_are_not_eligible(text: str) -> None:
    assert not eligible(text)
    assert split_reply(text, 0.0, 0.0) == [text]


def test_a_long_reply_can_become_three_messages_and_a_medium_one_only_two() -> None:
    assert len(split_reply(LONG, 0.0, 0.0)) == 3
    assert len(split_reply(THREE, 0.0, 0.0)) == 2


def test_the_cut_never_leaves_a_question_hanging_and_never_makes_a_tiny_part() -> None:
    text = (
        "oh that is a really interesting thing to have noticed about it. "
        "what made you think of it just now? "
        "i think it comes down to how the two ideas rub against each other in practice."
    )
    for pick in (0.0, 0.5, 0.99):
        parts = split_reply(text, 0.0, pick)
        assert all(not p.rstrip().endswith("?") for p in parts[:-1])
        assert all(len(p.split()) >= MIN_PART_WORDS for p in parts)


def test_pick_varies_where_it_is_cut_when_there_is_a_choice() -> None:
    even = " ".join(f"Sentence {n} has exactly a few more words in it." for n in range(4))
    firsts = {split_reply(even, 0.0, pick)[0] for pick in (0.0, 0.99)}
    assert len(firsts) == 2


def test_sentences_keeps_the_punctuation() -> None:
    assert sentences("One. Two! Three? Four…") == ["One.", "Two!", "Three?", "Four…"]


def test_a_reply_too_long_for_the_surface_is_cut_after_a_sentence() -> None:
    text = "One short sentence here. " + "word " * 30 + "end."
    parts = fit(text, 40)
    assert all(len(p) <= 40 for p in parts)
    assert parts[0] == "One short sentence here."
    assert " ".join(parts).split() == text.split()


def test_without_a_sentence_end_it_cuts_at_a_space_and_without_one_at_the_limit() -> None:
    assert fit("aaaa bbbb cccc", 9) == ["aaaa bbbb", "cccc"]
    assert fit("x" * 25, 10) == ["x" * 10, "x" * 10, "x" * 5]
    assert fit("fits", 10) == ["fits"]
