from __future__ import annotations

from collections.abc import Callable

from companion.core.relevance import build_prompt, eligible, parse
from companion.core.types import Belief, BeliefId, Frame, Json, Provenance
from companion.core.vectors import nearest, unit


def test_held_memories_only_when_they_share_and_never_crisis(belief: Callable[..., Belief]) -> None:
    plain, held, crisis = (belief(bid=b, sensitivity=n) for b, n in (("a", 0), ("b", 2), ("c", 3)))
    played = belief(bid="d", frame=Frame.PLAY, provenance=Provenance.PLAYED)
    pool = [plain, held, crisis, played]
    assert eligible(pool, sharing=False) == [plain]
    assert eligible(pool, sharing=True) == [plain, held]


def test_nearest_is_closest_first_and_skips_the_unembedded(belief: Callable[..., Belief]) -> None:
    a, b, c = belief(bid="a"), belief(bid="b"), belief(bid="c")
    vectors = {BeliefId("a"): unit([1, 0]), BeliefId("b"): unit([1, 1])}
    got = nearest(unit([0, 1]), [a, b, c], vectors)
    assert [x.id for x, _ in got] == ["b", "a"]


def test_picks_are_shown_labels_only_at_most_three(belief: Callable[..., Belief]) -> None:
    shortlist = [belief(bid=str(n), claim=f"The user likes thing {n}.") for n in range(5)]
    prompt = build_prompt("how was it?", "so good", shortlist)
    assert prompt.splitlines()[:2] == ["COMPANION: how was it?", "USER: so good"]
    assert "[r5] The user likes thing 4." in prompt
    data: Json = {"labels": ["r2", "[r2]", "r9", "r1", "r3", "r4"]}
    assert [b.id for b in parse(data, shortlist)] == ["1", "0", "2"]
    assert parse(None, shortlist) == []
