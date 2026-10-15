from __future__ import annotations

from collections.abc import Callable

import pytest

from companion.core.moves import MAX_HABIT_CHARS, MAX_HABITS, note_for, parse, replies_to_read
from companion.core.types import Speaker, Utterance


def _chat(utterance: Callable[..., Utterance], n: int) -> list[Utterance]:
    out: list[Utterance] = []
    for i in range(n):
        out.append(utterance(text="hm", uid=f"u{i}"))
        out.append(utterance(text=f"reply {i}", speaker=Speaker.COMPANION, uid=f"c{i}"))
    return out


def test_it_reads_the_last_replies_ending_with_the_one_just_sent(
    utterance: Callable[..., Utterance],
) -> None:
    got = replies_to_read(_chat(utterance, 8), "latest")
    assert got == ["reply 3", "reply 4", "reply 5", "reply 6", "reply 7", "latest"]


def test_too_few_replies_means_nothing_to_judge(utterance: Callable[..., Utterance]) -> None:
    assert replies_to_read(_chat(utterance, 2), "latest") == []


def test_parse_cleans_and_bounds_what_the_model_names() -> None:
    got = parse({"habits": ["  calls   them  sweetheart ", "", "x" * 500, "a", "b", "c"]})
    assert got is not None
    assert got[0] == "calls them sweetheart"
    assert len(got) == MAX_HABITS
    assert all(len(h) <= MAX_HABIT_CHARS for h in got)


@pytest.mark.parametrize("data", [None, "x", {}, {"habits": "no"}, {"habits": [1]}])
def test_parse_rejects_a_malformed_answer(data: object) -> None:
    assert parse(data) is None  # type: ignore[arg-type]


def test_an_empty_list_is_a_valid_answer_and_gives_no_note() -> None:
    assert parse({"habits": []}) == []
    assert note_for([]) is None


def test_the_note_names_each_habit_and_asks_for_something_different() -> None:
    note = note_for(["calls them sweetheart", "ends with a smirk"])
    assert note == (
        "[Your recent replies keep doing this: calls them sweetheart; ends with a smirk."
        " Do something different.]"
    )
