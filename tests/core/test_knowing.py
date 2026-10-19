from __future__ import annotations

from collections.abc import Callable

from companion.core.knowing import (
    Depth,
    Domain,
    Label,
    label_prompt,
    parse_labels,
    pick_gap,
)
from companion.core.types import Belief, BeliefId, Json


def _labels(pairs: list[tuple[str, Domain]]) -> dict[BeliefId, Label]:
    return {BeliefId(b): Label(BeliefId(b), d, Depth.SURFACE) for b, d in pairs}


def test_labels_keep_known_refs_and_values_once(belief: Callable[..., Belief]) -> None:
    text, refs = label_prompt([belief(bid="a", claim="The user likes tea."), belief(bid="b")])
    assert text.startswith("[r1] The user likes tea.")
    data: Json = {
        "labels": [
            {"ref": "r1", "domain": "interests", "depth": "surface"},
            {"ref": "r1", "domain": "values", "depth": "core"},
            {"ref": "r2", "domain": "astrology", "depth": "surface"},
            {"ref": "r9", "domain": "people", "depth": "surface"},
        ]
    }
    assert parse_labels(data, refs) == [Label(BeliefId("a"), Domain.INTERESTS, Depth.SURFACE)]
    assert parse_labels("nonsense", refs) == []


def test_the_gap_is_the_thinnest_askable_part(belief: Callable[..., Belief]) -> None:
    beliefs = [belief(bid=b) for b in "abcdefgh"]
    labels = _labels(
        [
            ("a", Domain.IDENTITY),
            ("b", Domain.PEOPLE),
            ("c", Domain.DAILY),
            ("d", Domain.INTERESTS),
            ("e", Domain.INTERESTS),
            ("f", Domain.HISTORY),
            ("g", Domain.VALUES),
            ("h", Domain.INNER),
        ]
    )
    gap = pick_gap(beliefs, labels)
    assert gap is not None
    assert gap.domain is Domain.HOPES
    assert gap.depth is Depth.SURFACE
    assert "hopes (0 memories" in gap.reason


def test_their_inner_life_is_never_the_gap(belief: Callable[..., Belief]) -> None:
    beliefs = [belief(bid=b) for b in "abcdefg"]
    askable = [Domain.IDENTITY, Domain.PEOPLE, Domain.DAILY, Domain.INTERESTS]
    askable += [Domain.HISTORY, Domain.HOPES, Domain.VALUES]
    labels = _labels([(b, d) for b, d in zip("abcdefg", askable, strict=True)])
    gap = pick_gap(beliefs, labels)
    assert gap is not None
    assert gap.domain is Domain.IDENTITY  # a tie goes to the first askable part, never inner


def test_closed_or_unlabelled_memories_do_not_count(belief: Callable[..., Belief]) -> None:
    assert pick_gap([belief(bid="a")], {}) is None
    gap = pick_gap([belief(bid="a")], _labels([("a", Domain.HOPES), ("gone", Domain.PEOPLE)]))
    assert gap is not None
    assert gap.counts == {Domain.HOPES: 1}
