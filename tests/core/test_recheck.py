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
    assert code_checks("ugh—the worst", "laundry") == ["an em dash"]


@pytest.mark.parametrize(
    "reply",
    [
        "sounds good 😌 [right now it is Thursday 13:11]",
        "Right now it is Friday 02:10. go to sleep",
        "<notes>hi</notes>",
        "ok <clock>",
    ],
)
def test_the_clock_line_or_a_tag_copied_into_a_reply_fails(reply: str) -> None:
    assert "the clock line or a tag copied from the system block" in code_checks(reply)


def test_talking_about_the_time_is_fine() -> None:
    assert code_checks("right now it is late, go to bed lol") == []
    assert code_checks("it's thursday already?") == []


def test_the_stock_especially_line_is_caught_and_plain_uses_are_not() -> None:
    stock = ["the stock 'X, especially when' line"]
    assert code_checks("that sounds exhausting, girl, especially when you're tired") == stock
    assert code_checks("that fear makes sense, especially with something this tangled") == stock
    assert code_checks("that sounds so good, especially the tiny shops") == stock
    assert code_checks("free food wins, even when the fish isn't your favorite") == stock
    assert code_checks("ugh, that's the worst") == []
    assert code_checks("i like jazz, especially piano") == []
    assert code_checks("what are you looking forward to, even if it's small?") == []


def test_a_beat_as_a_stage_direction_is_caught_but_not_a_beat_in_music() -> None:
    assert code_checks("*a beat, and I grin*") == ["the stage direction 'a beat'"]
    assert code_checks("the song has a beat drop that hits") == []


def test_markdown_titles_and_bold_are_caught_but_not_actions_or_scenes() -> None:
    from companion.core.recheck import MARKDOWN, code_checks  # noqa: PLC0415

    assert MARKDOWN in code_checks("mostly *Thor* and *The Avengers*")
    assert MARKDOWN in code_checks("that's **so** good")
    assert code_checks("*leans in and kisses you*") == []
    assert code_checks("*I rock back once, waiting*") == []
    assert code_checks("3*4 = 12 and 5*6") == []
    assert code_checks("watch *Thor* first", scene=True) == []
