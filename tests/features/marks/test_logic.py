from __future__ import annotations

from companion.features.marks.logic import EVERY, MARKS, note, offered, pick


def test_a_mark_is_never_one_they_just_used_or_one_it_used_lately() -> None:
    theirs = "lol ^^"
    recent = ["haha :>", "ok ✧"]
    picks = {pick(f"t{i}", theirs, recent) for i in range(300)}
    assert picks
    assert not picks & {"^^", ":>", "✧", None}


def test_with_every_mark_used_there_is_no_pick() -> None:
    assert pick("t", "", [" ".join(MARKS)]) is None


def test_their_mark_always_brings_an_offer_and_otherwise_about_one_turn_in_four() -> None:
    assert all(offered(f"t{i}", "nice :3") for i in range(50))
    rate = sum(offered(f"t{i}", "nice") for i in range(4000)) / 4000
    assert abs(rate - 1 / EVERY) < 0.03


def test_the_same_turn_always_gets_the_same_answer() -> None:
    assert offered("turn-1", "hey") == offered("turn-1", "hey")


def test_the_note_names_the_mark() -> None:
    assert "(╯°□°)╯︵ ┻━┻" in note("(╯°□°)╯︵ ┻━┻")


def test_the_list_holds_the_kaomoji_as_written() -> None:
    assert "(╯°□°)╯︵ ┻━┻" in MARKS
    assert "¯\\_(ツ)_/¯" in MARKS
    assert len(MARKS) == len(set(MARKS)) >= 20
