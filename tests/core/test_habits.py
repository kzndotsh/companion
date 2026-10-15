from __future__ import annotations

from collections.abc import Callable

from companion.core.habits import opener_note
from companion.core.types import Speaker, Utterance


def _chat(utterance: Callable[..., Utterance], replies: list[str]) -> list[Utterance]:
    out: list[Utterance] = []
    for i, text in enumerate(replies):
        out.append(utterance(text="hm", uid=f"u{i}"))
        out.append(utterance(text=text, speaker=Speaker.COMPANION, uid=f"c{i}"))
    return out


def test_three_of_the_last_five_openers_trigger_the_note(
    utterance: Callable[..., Utterance],
) -> None:
    prior = _chat(utterance, ["Ha, ok.", "sure", "Ha, fair.", "yes", "ha, true"])
    note = opener_note(prior)
    assert note is not None
    assert '3 of your last 5 replies began with "ha"' in note


def test_varied_openers_give_no_note(utterance: Callable[..., Utterance]) -> None:
    prior = _chat(utterance, ["Ha, ok.", "sure", "yes", "right", "Ha, true"])
    assert opener_note(prior) is None


def test_only_the_companions_words_count(utterance: Callable[..., Utterance]) -> None:
    prior = [utterance(text="ha ha ha", uid=f"u{i}") for i in range(5)]
    assert opener_note(prior) is None


def test_an_old_streak_outside_the_window_is_forgotten(
    utterance: Callable[..., Utterance],
) -> None:
    prior = _chat(utterance, ["Ha, a", "Ha, b", "Ha, c", "one", "two", "three", "four", "five"])
    assert opener_note(prior) is None


def test_nothing_said_yet_gives_no_note() -> None:
    assert opener_note([]) is None
