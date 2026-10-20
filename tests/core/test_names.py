from __future__ import annotations

from companion.core.names import Row, index, mentioned, parse, prompt, usable
from companion.core.types import BeliefId, Json

A, B = BeliefId("a"), BeliefId("b")


def test_only_words_worth_matching_are_kept() -> None:
    assert usable("Biscuit")
    assert usable("my sister")
    assert not usable("my")
    assert not usable("the you")
    assert not usable("ok")


def test_parse_keeps_refs_it_showed_and_drops_common_words() -> None:
    _, refs = prompt([(A, "Their dog Biscuit hates baths."), (B, "Biscuit is a corgi.")], [])
    data: Json = {
        "names": [
            {"name": "Biscuit", "aliases": ["Bis", "my", "the dog"], "refs": ["r1", "[r2]", "r9"]},
            {"name": "", "aliases": [], "refs": ["r1"]},
        ]
    }
    rows = parse(data, refs)
    assert rows == [
        Row(A, "Biscuit", ("biscuit", "bis", "the dog")),
        Row(B, "Biscuit", ("biscuit", "bis", "the dog")),
    ]
    assert parse({"oops": 1}, refs) is None


def test_a_name_is_matched_as_a_whole_word_over_current_memories_only() -> None:
    rows = [Row(A, "Biscuit", ("biscuit", "bis")), Row(B, "Biscuit", ("biscuit",))]
    named = index(rows, [A])
    assert [n.beliefs for n in named] == [frozenset({A})]
    assert mentioned("took biscuit to the park", named) == named
    assert mentioned("BIS is so lazy today", named) == named
    assert mentioned("ate a biscuits sandwich", named) == []
    assert mentioned("a bisque for lunch", named) == []
    assert index(rows, []) == []


def test_known_names_are_shown_so_the_model_reuses_them() -> None:
    text, refs = prompt([(A, "They love Saosin.")], ["Saosin", "Biscuit"])
    assert text.startswith("Known names: Biscuit, Saosin")
    assert "[r1] They love Saosin." in text
    assert refs == {"r1": A}
