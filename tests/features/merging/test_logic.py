from __future__ import annotations

from companion.features.merging.logic import agreed, read_claim, read_groups


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
