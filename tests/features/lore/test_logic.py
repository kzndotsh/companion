from __future__ import annotations

from collections.abc import Callable

from companion.core.types import Belief, BeliefId, Json, Subject
from companion.features.lore.logic import Kind, Labelled, agreed, lore, parse, prompt


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


def test_a_view_is_a_taste_only_when_every_read_agrees() -> None:
    a, b, c = BeliefId("a"), BeliefId("b"), BeliefId("c")
    taste = [Labelled(a, Kind.TASTE), Labelled(b, Kind.TASTE), Labelled(c, Kind.TASTE)]
    split = [Labelled(a, Kind.TASTE), Labelled(b, Kind.RULE)]  # c missing from this read
    got = agreed([taste, taste, split], [a, b, c])
    assert got == [Labelled(a, Kind.TASTE), Labelled(b, Kind.RULE), Labelled(c, Kind.STANCE)]
    assert agreed([taste, taste, None], [a]) == [Labelled(a, Kind.STANCE)]  # a failed read
