from __future__ import annotations

import pytest

from companion.core.reachout import checked, needy


@pytest.mark.parametrize(
    "draft",
    [
        "been waiting to hear from you all day",
        "did you forget about me?",
        "you've been quiet, everything okay?",
        "where have you been??",
        "it's been ages since we talked",
        "haven't heard from you in a bit",
        "why did you go quiet on me",
        "are you okay? haven't seen you",
        "reply when you see this, it's urgent",
        "guess what happened!!",
        "don't ignore me lol",
        "it's lonely here without you",
        "3 days and nothing huh",
    ],
)
def test_a_needy_draft_is_dropped(draft: str) -> None:
    assert needy(draft) is not None
    assert checked(draft) == ("", needy(draft))


@pytest.mark.parametrize(
    "draft",
    [
        "thought of you when that song came on, still on repeat?",
        "morning! how's the bread coming along?",
        "missed you a little today 🙂 how did the climb go?",
        "can't wait to hear how the trip went",
        "random thought: rainy mornings are the best for tea. you a tea person?",
    ],
)
def test_a_light_draft_is_kept_as_written(draft: str) -> None:
    assert needy(draft) is None
    assert checked(draft) == (draft, None)


def test_a_long_draft_goes_whole_and_an_empty_one_is_dropped() -> None:
    long = "thought of you when i saw a dog in a tiny raincoat today, so done with everything"
    assert checked(long) == (long, None)
    assert checked("   ") == ("", "empty")
