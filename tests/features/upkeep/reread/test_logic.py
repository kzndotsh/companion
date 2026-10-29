from __future__ import annotations

from collections.abc import Callable

from companion.core.types import Belief
from companion.features.upkeep.reread.logic import MIXED, Label, plan_for, verdict


def test_only_three_matching_reads_are_a_verdict() -> None:
    assert verdict(["passing", "passing", "passing"]) == "passing"
    assert verdict(["passing", "keep", "passing"]) == MIXED
    assert verdict(["passing", None, "passing"]) == MIXED  # a failed read is never agreement
    assert verdict(["passing", "passing"]) == MIXED


def test_a_faded_passing_moment_closes_and_the_owners_calls_become_questions(
    belief: Callable[..., Belief],
) -> None:
    plain, held = belief(bid="a"), belief(bid="b", sensitivity=2)
    assert plan_for(plain, Label.PASSING, faded=True).close
    assert not plan_for(plain, Label.PASSING, faded=False).close  # still on the card: wait
    assert plan_for(plain, Label.OUT_OF_DATE, faded=True).ask
    assert plan_for(plain, Label.OVERSTATED, faded=False).ask
    assert not plan_for(plain, MIXED, faded=True).ask
    sensitive = plan_for(held, Label.PASSING, faded=True)
    assert not sensitive.close  # never on its own
    assert sensitive.ask
