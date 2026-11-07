import pytest

from companion.features.upkeep.merging.logic import Earlier, Noted, Picked, Settled, decode, encode


@pytest.mark.parametrize(
    ("answer", "stored"),
    [
        (Settled.APART, "apart"),
        (Settled.GONE, "gone"),
        (Noted("only for tonight"), "note: only for tonight"),
        (Picked((1, 2, 4)), "pick 1 2 4"),
    ],
)
def test_an_answer_is_stored_as_the_same_text_it_always_was(answer: object, stored: str) -> None:
    assert encode(answer) == stored  # type: ignore[arg-type]
    assert decode(stored) == answer


def test_no_answer_decodes_to_none() -> None:
    assert decode(None) is None


def test_an_answer_in_an_older_form_closes_the_question() -> None:
    for stored in ("reworded as one", "superseded by 124: wording not in their words"):
        got = decode(stored)
        assert got == Earlier(stored)
        assert encode(Earlier(stored)) == stored
