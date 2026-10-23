from __future__ import annotations

from companion.features.topics.logic import MOVES, move_for, topic_note


def test_the_move_follows_the_clock_and_a_plan_offered_this_turn_comes_first() -> None:
    assert move_for(10, loop_offered=False) is MOVES["day"]
    assert move_for(18, loop_offered=False) is MOVES["evening"]
    assert move_for(23, loop_offered=False) is MOVES["night"]
    assert move_for(3, loop_offered=False) is MOVES["night"]
    assert move_for(23, loop_offered=True) is MOVES["loop"]


def _note(
    *, spent: bool = True, casual: bool = True, moved_recently: bool = False
) -> tuple[str, object] | None:
    return topic_note(
        spent=spent, casual=casual, moved_recently=moved_recently, local_hour=15, loop_offered=False
    )


def test_the_note_only_on_a_casual_spent_turn_not_moved_recently() -> None:
    found = _note()
    assert found is not None
    assert MOVES["day"].text in found[0]
    assert _note(spent=False) is None
    assert _note(casual=False) is None
    assert _note(moved_recently=True) is None
