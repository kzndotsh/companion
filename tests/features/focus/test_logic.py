from __future__ import annotations

from companion.core.types import BeliefId
from companion.core.vectors import unit
from companion.features.focus.logic import closeness, moment_texts


def test_a_short_message_is_read_with_the_reply_it_answers() -> None:
    assert moment_texts("lol", "the dog stole a sock") == ["lol", "the dog stole a sock\nlol"]
    assert moment_texts("hi", None) == ["hi"]


def test_closeness_is_the_best_score_against_either_query() -> None:
    dogs, food = BeliefId("dogs"), BeliefId("food")
    vectors = {dogs: unit([1, 0]), food: unit([0, 1])}
    scores = closeness([unit([0, 1]), unit([1, 1])], vectors)
    assert round(scores[food], 3) == 1.0
    assert round(scores[dogs], 3) == round(2**-0.5, 3)
