from __future__ import annotations

from collections.abc import Callable

import pytest

from companion.core.basics import ASK_NAME, ask_name, asked_for_name, knows_name, parse_name
from companion.core.types import Belief, Subject


@pytest.mark.parametrize(
    "claim",
    [
        "The user's name is Sam.",
        "The user's first name is Sam.",
        "The user goes by Sam.",
        "The user wants to be called Sam.",
        "The user prefers being called Sam.",
        "The user is called Sam by friends.",
    ],
)
def test_a_belief_that_says_what_they_are_called_counts(
    belief: Callable[..., Belief], claim: str
) -> None:
    assert knows_name([belief(bid="b", claim=claim)])


@pytest.mark.parametrize(
    "claim",
    [
        "The user has two dogs named Juju and Foxy.",
        "The user wants the companion's name to be witty.",
        "The user says being called the wrong word is complex for them.",
    ],
)
def test_names_of_others_or_the_companion_do_not_count(
    belief: Callable[..., Belief], claim: str
) -> None:
    assert not knows_name([belief(bid="b", claim=claim)])


def test_a_belief_about_the_companion_does_not_count(belief: Callable[..., Belief]) -> None:
    assert not knows_name([belief(bid="b", claim="The user's name is Sam.", subject=Subject.SELF)])


def test_it_asks_only_when_unknown_casual_and_not_asked_today() -> None:
    assert ask_name(known=False, casual=True, asked_recently=False) == ASK_NAME.text
    assert ask_name(known=True, casual=True, asked_recently=False) is None
    assert ask_name(known=False, casual=False, asked_recently=False) is None
    assert ask_name(known=False, casual=True, asked_recently=True) is None


@pytest.mark.parametrize(
    ("reply", "asked"),
    [
        ("what name do you like being called?", True),
        ("wait, what's your name?", True),
        ("what should i call you?", True),
        ("i'll remember that name for you.", False),
        ("your name suits you", False),
    ],
)
def test_it_knows_when_it_asked_what_to_call_them(reply: str, *, asked: bool) -> None:
    assert asked_for_name(reply) is asked


@pytest.mark.parametrize(
    ("data", "said", "name"),
    [
        ({"name": "Kai"}, "Kai", "Kai"),
        ({"name": "Kai."}, "it's kai lol", "Kai"),
        ({"name": ""}, "not telling you yet 😏", None),
        ({"name": "Alexandra"}, "call me alex", None),
        ({"name": "the one and only queen"}, "the one and only queen", None),
    ],
)
def test_a_name_is_kept_only_if_short_and_in_their_own_words(
    data: dict[str, str], said: str, name: str | None
) -> None:
    assert parse_name(data, said) == name  # type: ignore[arg-type]
