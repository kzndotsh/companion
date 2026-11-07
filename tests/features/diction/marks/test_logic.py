from __future__ import annotations

import pytest

from companion.features.diction.marks import logic as marks_logic
from companion.features.diction.marks.logic import EVERY, MARKS, note, offered, pick


def test_a_mark_is_never_one_they_just_used_or_one_it_used_lately() -> None:
    theirs = "lol ^^"
    recent = ["haha :>", "ok ✧"]
    picks = {pick(f"t{i}", theirs, recent) for i in range(300)}
    assert picks
    assert not picks & {"^^", ":>", "✧", None}


def test_with_every_mark_used_there_is_no_pick() -> None:
    assert pick("t", "", [" ".join(MARKS)]) is None


def test_their_mark_always_brings_an_offer_and_a_playful_message_about_half_the_time() -> None:
    assert all(offered(f"t{i}", "nice :3") for i in range(50))
    rate = sum(offered(f"t{i}", "lol nice") for i in range(4000)) / 4000
    assert abs(rate - 1 / EVERY) < 0.03


def test_a_plain_message_never_brings_an_offer() -> None:
    assert not any(offered(f"t{i}", "went to the store") for i in range(500))


def test_no_offer_while_one_of_its_last_few_replies_has_a_mark() -> None:
    recent = ["sounds fun (¬‿¬)", "ok", "sure"]
    assert not any(offered(f"t{i}", "hahaha 😂", recent) for i in range(200))
    assert any(offered(f"t{i}", "hahaha 😂", ["ok", "sure", "nice"]) for i in range(200))


def test_the_same_turn_always_gets_the_same_answer() -> None:
    assert offered("turn-1", "hey") == offered("turn-1", "hey")


def test_the_note_names_the_mark() -> None:
    assert "(╯°□°)╯︵ ┻━┻" in note("(╯°□°)╯︵ ┻━┻")


def test_when_they_used_a_mark_the_note_names_it_as_theirs() -> None:
    offer = note("(｡•̀ᴗ-)✧", "some chicken and tater tots :3")
    assert ":3" in offer
    assert "(｡•̀ᴗ-)✧" in offer
    assert ":3" not in note("(｡•̀ᴗ-)✧", "some chicken and tater tots")


def test_the_list_has_no_duplicates_and_enough_marks_to_rotate() -> None:
    assert len(MARKS) == len(set(MARKS)) >= 20


def _is_still_free(mark: str, said: str, monkeypatch: pytest.MonkeyPatch) -> bool:
    """With `mark` the only mark there is, whether `pick` can still give it after `said`."""
    monkeypatch.setattr(marks_logic, "MARKS", (mark,))
    return pick("t", said, []) == mark


def test_a_mark_counts_as_used_only_where_it_stands_on_its_own(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _is_still_free("✧", "so cute (｡•̀ᴗ-)✧", monkeypatch)
    assert not _is_still_free("✧", "so cute ✧", monkeypatch)
    assert not _is_still_free("^^", "ok ^^", monkeypatch)
    assert not _is_still_free("uwu", "uwu hi", monkeypatch)
    assert _is_still_free("uwu", "uwuuu", monkeypatch)
