from __future__ import annotations

import pytest

from companion.core.energy import texting_energy


@pytest.mark.parametrize(
    ("text", "score"),
    [
        ("ok", 0),
        ("made pasta for dinner", 0),
        ("i'm so tired of all of this", 0),
        ("haha nice :p", 1),
        ("checking DNS and WHOIS records", 0),
        ("omg YESSS!!! 😭", 3),
        ("noooo way!! 😂😂😂", 4),
        ("yaaaaay 😊", 2),
    ],
)
def test_energy_counts_stretched_words_exclamations_emoji_and_emoticons(
    text: str, score: int
) -> None:
    assert texting_energy(text) == score


@pytest.mark.parametrize(
    "text", ["ugh noooo!! :(", "this sucks!! 😭", "so annoyed rn!!!", "nooo 😢😢", "D: whyyy"]
)
def test_a_sad_or_annoyed_message_is_not_happy_energy(text: str) -> None:
    assert texting_energy(text) == 0


def test_no_one_kind_of_mark_counts_as_a_whole_mood() -> None:
    assert texting_energy("!" * 40) == texting_energy("!!") == 1
    assert texting_energy("😂" * 20) == 2


def test_a_pasted_block_is_not_typing() -> None:
    pasted = "here!!\n" + "\n".join(f"| row {n} | :D |" for n in range(6))
    assert texting_energy(pasted) == 0
    assert texting_energy("yesss!! " * 60) == 0
