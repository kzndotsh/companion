from __future__ import annotations

from collections.abc import Callable

from companion.core.types import Belief, BeliefKind
from companion.features.upkeep.merging.logic import (
    agreed,
    kept_wording,
    read_claim,
    read_groups,
    unsupported,
)


def test_groups_are_read_from_labels_and_bad_labels_are_ignored() -> None:
    assert read_groups({"groups": [["m1", "[m3]"], ["m2"], ["m9", "m4"]]}, 5) == [frozenset({0, 2})]
    assert read_groups({"nope": []}, 5) is None


def test_only_pairs_every_read_puts_together_count() -> None:
    a = [frozenset({0, 1, 2}), frozenset({4, 5})]
    b = [frozenset({0, 1}), frozenset({2, 3}), frozenset({4, 5})]
    c = [frozenset({0, 1, 2, 3}), frozenset({4, 5})]
    assert agreed([a, b, c]) == [frozenset({0, 1}), frozenset({4, 5})]


def test_agreed_pairs_that_share_a_memory_join_into_one_group() -> None:
    reads = [[frozenset({0, 1, 2})]] * 3
    assert agreed(reads) == [frozenset({0, 1, 2})]


def test_a_failed_or_empty_read_is_never_agreement() -> None:
    g = [frozenset({0, 1})]
    assert agreed([g, g, None]) == []
    assert agreed([g, g, []]) == []
    assert agreed([g, g]) == []


def test_the_writer_can_say_keep_apart() -> None:
    assert read_claim({"claim": " Has  two dogs. ", "keep_apart": False}) == "Has two dogs."
    assert read_claim({"claim": "x", "keep_apart": True}) is None
    assert read_claim({"claim": "", "keep_apart": False}) is None


def test_a_wording_may_not_add_a_name_a_number_or_drop_a_date(
    belief: Callable[..., Belief],
) -> None:
    members = [
        belief(bid="a", quote="my dog rex", claim="On 2026-10-25 the user walked their dog Rex."),
        belief(bid="b", quote="its about time for bed", claim="The user was going to bed."),
    ]
    assert unsupported("On 2026-10-25 the user walked Rex and went to bed.", members) == []
    assert unsupported("On 2026-10-25 the user walked Rex and Maya.", members) == ["Maya"]
    assert unsupported("On 2026-10-25 the user went to bed around 1am.", members) == ["1am"]
    assert unsupported("The user walks their dog Rex.", members) == ["dropped 2026-10-25"]


def test_the_kept_wording_is_the_fullest_member_of_the_merged_kind(
    belief: Callable[..., Belief],
) -> None:
    members = [
        belief(bid="a", claim="Likes the holiday film.", kind=BeliefKind.PREFERENCE),
        belief(bid="b", claim="Names the holiday film as a favourite.", kind=BeliefKind.PREFERENCE),
        belief(
            bid="c", claim="Feels festive tonight about the holiday film.", kind=BeliefKind.STATE
        ),
    ]
    assert kept_wording(members) == "Feels festive tonight about the holiday film."
    assert kept_wording(members[:2]) == "Names the holiday film as a favourite."
