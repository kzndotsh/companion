from __future__ import annotations

from collections.abc import Callable

from companion.core.types import Belief, BeliefId, Frame, Json, Provenance
from companion.core.vectors import nearest, unit
from companion.features.recall.logic import SHOWN, build_prompt, eligible, extras, parse


def test_held_memories_only_when_they_share_and_never_crisis(belief: Callable[..., Belief]) -> None:
    plain, held, crisis = (belief(bid=b, sensitivity=n) for b, n in (("a", 0), ("b", 2), ("c", 3)))
    played = belief(bid="d", frame=Frame.PLAY, provenance=Provenance.PLAYED)
    pool = [plain, held, crisis, played]
    assert eligible(pool, asked=False, sharing=False) == [plain]
    assert eligible(pool, asked=False, sharing=True) == [plain, held]


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


def test_asked_reaches_crisis_level_but_never_a_hidden_memory(
    belief: Callable[..., Belief],
) -> None:
    plain, crisis, lane = (belief(bid=b, sensitivity=n) for b, n in (("a", 0), ("c", 3), ("i", 0)))
    hidden = frozenset({BeliefId("i")})
    assert eligible([plain, crisis, lane], asked=True, sharing=False, hidden=hidden) == [
        plain,
        crisis,
    ]
    assert eligible([plain, lane], asked=False, sharing=True, hidden=hidden) == [plain]


def test_a_near_pick_is_shown_once_and_never_beside_the_same_on_the_card() -> None:
    near = [(BeliefId(b), f"claim {b}") for b in "abcd"]
    got = extras(near, on_card=frozenset({BeliefId("a")}), recalled=[BeliefId("b")])
    assert got == ["claim c", "claim d"][:SHOWN]
