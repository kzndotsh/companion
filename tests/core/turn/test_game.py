from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest

from companion.core.turn.game import NOTE, asking_game, game_note
from companion.core.types import Speaker, Utterance


@pytest.mark.parametrize(
    "asked",
    [
        "Ask me anything",
        "ok, ask something else",
        "Lead the way :3 or ask anything",
        "wanna ask me more questions? don't be shy",
        "Ask more!",
        "quiz me",
    ],
)
def test_telling_it_to_ask_starts_the_game(utterance: Callable[..., Utterance], asked: str) -> None:
    said = utterance(text=asked, speaker=Speaker.USER)
    later = said.at + timedelta(minutes=1)
    assert asking_game([said], "they talk to the locals", later)
    assert game_note([said], "they talk to the locals", later) == NOTE.text


@pytest.mark.parametrize(
    "said",
    [
        "btw do you notice you ask questions every single turn lol",
        "I'm gonna ask something silly but uhhh",
        "can i ask you something",
    ],
)
def test_mentioning_asking_is_not_a_game(utterance: Callable[..., Utterance], said: str) -> None:
    u = utterance(text=said, speaker=Speaker.USER)
    assert not asking_game([u], "so yeah", u.at + timedelta(minutes=1))


def test_a_pause_or_a_few_messages_or_calling_it_off_ends_it(
    utterance: Callable[..., Utterance],
) -> None:
    asked = utterance(text="ask me anything", speaker=Speaker.USER)
    soon = asked.at + timedelta(minutes=1)
    assert not asking_game([asked], "i drank my coffee", asked.at + timedelta(minutes=25))
    assert not asking_game([asked], "ok enough questions lol", soon)
    later = [asked, utterance(text="hmm"), utterance(text="idk")]
    assert asking_game(later[:2], "anyway", later[1].at + timedelta(minutes=1))
    assert not asking_game(later, "anyway", later[2].at + timedelta(minutes=1))  # past their last 3
