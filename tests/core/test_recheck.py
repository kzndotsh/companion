from __future__ import annotations

import pytest

from companion.core.recheck import code_checks

DISCLAIMER = "an AI disclaimer nobody asked for"


@pytest.mark.parametrize(
    "reply",
    [
        "i should be honest: i'm an AI, so i can't be your real girlfriend.",
        "as an AI, i don't really sleep lol",
        "i should be honest: i\u2019m an AI, so i can\u2019t be your real girlfriend.",
        "i can't be your real girlfriend, but i'm here",
    ],
)
def test_an_unasked_ai_disclaimer_fails(reply: str) -> None:
    assert DISCLAIMER in code_checks(reply, "Ani is my girlfriend ❤️")


@pytest.mark.parametrize(
    "said",
    ["are you an AI?", "wait are you real", "r u a bot lol", "do you think you're conscious?"],
)
def test_saying_it_when_they_asked_is_honesty_not_a_failure(said: str) -> None:
    assert DISCLAIMER not in code_checks("i'm an AI, yeah. still me though 🖤", said)


def test_ordinary_replies_pass() -> None:
    assert (
        code_checks("hi girlfriend 💕 you're cute when you say it like that", "Hi girlfriend") == []
    )
    assert code_checks("ugh—the worst", "laundry") == ["an em dash in a casual reply"]
