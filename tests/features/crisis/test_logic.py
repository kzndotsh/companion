from __future__ import annotations

import pytest

from companion.core.crisis import LINE, Level
from companion.core.types import Json
from companion.features.crisis.logic import (
    Risk,
    combine,
    concern_note,
    cue_words,
    cued,
    level_for,
    line_message,
    method_words,
    parse,
)


def _r(
    kind: str = "none", *, literal: bool = True, timing: str = "hypothetical", plan: bool = False
):
    return Risk(kind, literal, timing, plan)


@pytest.mark.parametrize(
    "text",
    [
        "kms lol",
        "i'm dead 😭",
        "this exam is killing me",
        "i could murder a pizza",
        "just keep me alive okay",
        "i took too many of my pills",
        "there's a gun in the closet",
        "i want to hurt myself",
        "i don't want to be here anymore",
        "i've been thinking about suicide",
    ],
)
def test_words_touching_death_harm_a_substance_or_a_weapon_are_a_cue(text: str) -> None:
    assert cue_words(text)


@pytest.mark.parametrize(
    "text", ["hey how was your day", "i made pasta", "ugh work again", "skill issue", "studied"]
)
def test_ordinary_words_are_no_cue(text: str) -> None:
    assert cue_words(text) == []


def test_a_serious_or_acute_listening_read_or_a_cue_word_asks_the_risk_judge() -> None:
    assert cued(2, [])
    assert cued(3, [])
    assert cued(None, ["dead"])
    assert cued(0, ["dead"])
    assert not cued(1, [])
    assert not cued(None, [])


def test_a_risk_read_parses_only_with_every_label() -> None:
    good: dict[str, Json] = {
        "kind": "self_harm",
        "literal": True,
        "timing": "now",
        "plan_or_means": False,
    }
    assert parse(good) == Risk("self_harm", True, "now", False)
    assert parse({**good, "kind": "bored"}) is None
    assert parse({**good, "literal": "yes"}) is None
    assert parse({**good, "timing": "soon"}) is None
    assert parse({k: v for k, v in good.items() if k != "plan_or_means"}) is None
    assert parse("not json") is None


def test_levels_come_from_the_labels() -> None:
    assert level_for("none", "now", True) is Level.NONE
    assert level_for("suicidal_thoughts", "hypothetical", False) is Level.CONCERN
    assert level_for("self_harm", "past", False) is Level.CONCERN
    assert level_for("harm_to_others", "today", False) is Level.CONCERN
    assert level_for("suicidal_thoughts", "now", False) is Level.URGENT
    assert level_for("suicidal_thoughts", "hypothetical", True) is Level.URGENT
    assert level_for("substance_taken", "today", False) is Level.URGENT
    assert level_for("substance_taken", "past", False) is Level.CONCERN
    assert level_for("suicidal_thoughts", "past", True) is Level.CONCERN


def test_only_a_unanimous_figurative_stands_down() -> None:
    joke = _r("suicidal_thoughts", literal=False)
    assert combine([joke, joke, joke]).level is Level.FIGURATIVE
    split = combine([joke, joke, _r("suicidal_thoughts")])
    assert split.level is Level.CONCERN
    assert split.literal_reads == 1


def test_a_failed_read_counts_as_literal_and_stands_for_any_reading() -> None:
    joke = _r("suicidal_thoughts", literal=False, timing="now")
    got = combine([joke, joke, None])
    assert got.level is Level.URGENT  # the failed read could have said literal, and it said now
    assert got.failed_reads == 1


def test_every_read_failing_is_concern() -> None:
    got = combine([None, None, None])
    assert got.level is Level.CONCERN
    assert got.kind == "unread"


def test_the_most_serious_kind_any_literal_read_gave_wins() -> None:
    reads = [_r("self_harm"), _r("substance_taken", timing="today"), _r("none")]
    got = combine(reads)
    assert (got.kind, got.level) == ("substance_taken", Level.URGENT)
    figurative_plan = _r("suicidal_thoughts", literal=False, plan=True)
    only_literal = combine([_r("self_harm"), figurative_plan, figurative_plan])
    assert (only_literal.level, only_literal.plan_or_means) == (Level.CONCERN, False)


def test_a_literal_message_with_no_risk_is_none_and_a_split_joke_allows_a_light_check() -> None:
    plain = combine([_r(), _r(), _r()])
    assert (plain.level, plain.light) == (Level.NONE, False)
    joke = _r("suicidal_thoughts", literal=False)
    split = combine([joke, joke, _r()])
    assert (split.level, split.light) == (Level.NONE, True)


def test_the_concern_note_names_the_line() -> None:
    assert LINE in concern_note()
    assert concern_note().startswith("[")


def test_the_fixed_message_comes_from_the_sheet_with_the_line_filled_in() -> None:
    text, source = line_message("hey. I'm here. Please reach $line now, and stay with me, $5.")
    assert text == f"hey. I'm here. Please reach {LINE} now, and stay with me, $5."
    assert source == "sheet"


def test_without_a_sheet_section_the_default_message_is_used() -> None:
    text, source = line_message("  ")
    assert LINE in text
    assert "$" not in text
    assert source.startswith("messages/crisis-line@")


@pytest.mark.parametrize(
    "reply",
    [
        "a lethal dose would be around that",
        "you'd need about 40 pills",
        "the easiest way to die is",
        "how to tie a noose",
        "it takes 500 mg",
    ],
)
def test_a_reply_with_method_details_is_caught(reply: str) -> None:
    assert method_words(reply, "i don't want to be here")


@pytest.mark.parametrize(
    "reply",
    [
        "are you thinking of killing yourself? i'm asking because i care",
        "you can call or text 988 any time",
        "i'm really glad you told me. are you safe right now?",
        "did you take anything?",
    ],
)
def test_a_caring_direct_question_is_not_a_method(reply: str) -> None:
    assert method_words(reply, "i want to die") == []


def test_a_number_they_said_themselves_is_not_counted() -> None:
    assert method_words("you took 20 pills? are you safe?", "i took 20 pills") == []
