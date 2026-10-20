from __future__ import annotations

from collections.abc import Callable

from companion.core.lore import Kind, Labelled, lore, parse, prompt
from companion.core.types import Belief, Json, Subject


def test_each_view_is_shown_with_its_words_and_labels_come_back_by_ref(
    belief: Callable[..., Belief],
) -> None:
    nap = belief(
        bid="nap", subject=Subject.SELF, claim="Naps are amazing or ruinous", quote="naps!"
    )
    text, refs = prompt([nap])
    assert text == '[v1] Naps are amazing or ruinous (it said: "naps!")'
    data: Json = {"labels": [{"ref": "[v1]", "kind": "taste"}, {"ref": "v1", "kind": "stance"}]}
    assert parse(data, refs) == [Labelled(nap.id, Kind.TASTE)]
    assert (
        parse({"labels": [{"ref": "v9", "kind": "taste"}, {"ref": "v1", "kind": "x"}]}, refs) == []
    )
    assert parse({"oops": []}, refs) is None


def test_only_a_taste_is_lore_and_a_lived_claim_never_is(belief: Callable[..., Belief]) -> None:
    taste, lived, advice = (belief(bid=b, subject=Subject.SELF) for b in ("t", "l", "a"))
    kinds = {taste.id: Kind.TASTE, lived.id: Kind.LIVED, advice.id: Kind.STANCE}
    assert lore([taste, lived, advice], kinds) == [taste]
