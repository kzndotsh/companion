from __future__ import annotations

from collections.abc import Callable

import pytest

from companion.core.turn.habits import echo_note, habit_note, has_marks, opener_note, pet_words
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


def test_a_phrase_reused_across_replies_is_named(utterance: Callable[..., Utterance]) -> None:
    from companion.core.turn.habits import repeated_phrases  # noqa: PLC0415

    prior = _chat(
        utterance,
        [
            "*keeps the blanket snug around you* there",
            "okay, the blanket snug around you again",
            "*wraps the blanket snug around you* cozy",
            "something else entirely",
        ],
    )
    assert repeated_phrases(prior) == ["blanket snug around"]


def test_function_words_alone_are_not_a_habit(utterance: Callable[..., Utterance]) -> None:
    from companion.core.turn.habits import repeated_phrases  # noqa: PLC0415

    prior = _chat(utterance, ["and then i am here", "so and then i am there", "and then i am ok"])
    assert repeated_phrases(prior) == []


def test_the_phrase_must_come_from_enough_different_replies(
    utterance: Callable[..., Utterance],
) -> None:
    from companion.core.turn.habits import repeated_phrases  # noqa: PLC0415

    prior = _chat(utterance, ["snug blanket around you, snug blanket around you", "different"])
    assert repeated_phrases(prior) == []


def test_the_habit_note_joins_opener_and_phrase_notes(
    utterance: Callable[..., Utterance],
) -> None:
    from companion.core.turn.habits import habit_note  # noqa: PLC0415

    prior = _chat(
        utterance,
        ["Ha, soft cozy burrito now", "Ha, soft cozy burrito time", "Ha, soft cozy burrito"],
    )
    note = habit_note(prior)
    assert note is not None
    assert 'began with "ha"' in note
    assert "soft cozy burrito" in note
    assert habit_note(_chat(utterance, ["one", "two"])) is None


@pytest.mark.parametrize(
    ("text", "marked"),
    [
        ("i try i try :P", True),
        ("yaaaaay 😊", True),
        ("home finally :3", True),
        ("haha xD", True),
        ("hmm :/ idk", True),
        ("see https://a.b/c", False),
        ("10:30 tomorrow", False),
        ("lol ok", False),
    ],
)
def test_an_emoji_or_emoticon_is_found_and_urls_and_times_are_not(
    text: str, *, marked: bool
) -> None:
    assert has_marks(text) is marked
    assert (echo_note(text) is not None) is marked


def test_a_word_it_keeps_reaching_for_is_named_on_a_casual_turn(
    utterance: Callable[..., Utterance],
) -> None:
    replies = [
        "a tiny goth tater tot in your pocket",
        "tiny coffee it is, enjoy",
        "what's a tiny detail that makes you trust it?",
    ]
    prior = [utterance(text=r, speaker=Speaker.COMPANION) for r in replies]
    assert pet_words(prior) == ["tiny"]
    assert '"tiny"' in (habit_note(prior, words=True) or "")
    assert habit_note(prior) is None  # not counted off a casual turn


def test_a_word_they_used_is_their_topic_not_its_habit(
    utterance: Callable[..., Utterance],
) -> None:
    prior = [
        utterance(text="i drank my coffee", speaker=Speaker.USER),
        *(utterance(text=f"coffee round {i}", speaker=Speaker.COMPANION) for i in range(3)),
    ]
    assert "coffee" not in pet_words(prior)
