from __future__ import annotations

from collections.abc import Callable

from companion.core.types import Belief
from companion.features.guess.logic import likely, note, offerable, parse


def test_only_short_questions_reach_the_judge() -> None:
    assert likely("you know what time it is?")
    assert not likely("ok coffee time")
    assert not likely(
        "so i was thinking about whether we should maybe go somewhere tonight or not?"
    )


def test_an_invitation_names_what_to_guess() -> None:
    assert (
        parse({"invited": True, "about": "what it is time for them"}) == "what it is time for them"
    )
    assert parse({"invited": False, "about": ""}) is None
    assert parse({"invited": True, "about": " "}) is None
    assert parse("nope") is None


def test_the_note_offers_only_what_is_not_sensitive_and_needs_something(
    belief: Callable[..., Belief],
) -> None:
    coffee = belief(bid="c", claim="The user loves the ritual of coffee.")
    held = belief(bid="h", claim="something private", sensitivity=2)
    assert offerable([coffee, held]) == [coffee]
    text = note("what it is time for them", [coffee])
    assert text is not None
    assert "- The user loves the ritual of coffee." in text
    assert "as a question" in text
    assert note("x", []) is None
