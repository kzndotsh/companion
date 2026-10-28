from __future__ import annotations

from companion.core.turn.mentions import MentionCandidate, Rank, choose


def _c(rank: Rank, about: str = "x") -> MentionCandidate:
    return MentionCandidate(rank, f"[{about}]", False, "k", about)


def test_the_best_rank_wins_and_equal_ranks_keep_their_order() -> None:
    assert choose([_c(Rank.FOLLOW_UP), _c(Rank.THEIRS, "bday")], []) == _c(Rank.THEIRS, "bday")
    assert choose([_c(Rank.DAY, "a"), _c(Rank.DAY, "b")], []) == _c(Rank.DAY, "a")
    assert choose([], []) is None


def test_one_a_day_unless_what_came_before_ranks_lower() -> None:
    assert choose([_c(Rank.FOLLOW_UP)], [Rank.DAY]) is None  # a holiday this morning holds it
    assert choose([_c(Rank.THEIRS)], [Rank.THEIRS]) is None  # their day is marked once
    assert choose([_c(Rank.THEIRS)], [Rank.FOLLOW_UP]) == _c(Rank.THEIRS)  # never waits behind it
