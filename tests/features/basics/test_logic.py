from __future__ import annotations

from collections.abc import Callable

import pytest

from companion.core.types import Belief, Subject
from companion.features.basics.logic import (
    ASK_NAME,
    ASK_PRONOUNS,
    ask_name,
    ask_pronouns,
    asked_for_name,
    asked_for_pronouns,
    knows_name,
    parse_name,
    parse_pronouns,
)


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
        "The user has two dogs named Pepper and Biscuit.",
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
        ({"name": "Robin"}, "Robin", "Robin"),
        ({"name": "Robin."}, "it's robin lol", "Robin"),
        ({"name": ""}, "not telling you yet 😏", None),
        ({"name": "Alexandra"}, "call me alex", None),
        ({"name": "the one and only queen"}, "the one and only queen", None),
    ],
)
def test_a_name_is_kept_only_if_short_and_in_their_own_words(
    data: dict[str, str], said: str, name: str | None
) -> None:
    assert parse_name(data, said) == name  # type: ignore[arg-type]


def test_it_asks_pronouns_only_when_unset_casual_after_the_name_and_not_asked_today() -> None:
    ok = {
        "address_set": False,
        "name_known": True,
        "casual": True,
        "name_asked": False,
        "asked_recently": False,
    }
    assert ask_pronouns(**ok) == ASK_PRONOUNS.text
    assert ask_pronouns(**(ok | {"address_set": True})) is None
    assert ask_pronouns(**(ok | {"name_known": False})) is None  # the name comes first
    assert ask_pronouns(**(ok | {"name_asked": True})) is None  # not the day the name was asked
    assert ask_pronouns(**(ok | {"casual": False})) is None
    assert ask_pronouns(**(ok | {"asked_recently": True})) is None


@pytest.mark.parametrize(
    ("reply", "asked"),
    [
        ("btw what pronouns do you use?", True),
        ("is it she or he, or something else?", True),
        ("how should i refer to you?", True),
        ("what should i call you?", False),  # that is the name
        ("pronouns are personal", False),
    ],
)
def test_it_knows_when_it_asked_their_pronouns(reply: str, *, asked: bool) -> None:
    assert asked_for_pronouns(reply) is asked


@pytest.mark.parametrize(
    ("data", "said", "pronouns"),
    [
        ({"pronouns": "she/her"}, "she/her!", "she/her"),
        ({"pronouns": "she/her"}, "oh it's She / Her", "she/her"),
        ({"pronouns": "they/them"}, "he/him", None),
        ({"pronouns": "she/her"}, "she's fine with anything", None),
        ({"pronouns": ""}, "why do you ask lol", None),
        (
            {"pronouns": "any pronouns are fine with me honestly"},
            "any pronouns are fine with me honestly",
            None,
        ),
    ],
)
def test_pronouns_are_kept_only_if_short_and_in_their_own_words(
    data: dict[str, str], said: str, pronouns: str | None
) -> None:
    assert parse_pronouns(data, said) == pronouns  # type: ignore[arg-type]
