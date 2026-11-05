from __future__ import annotations

from collections.abc import Callable

import pytest

from companion.core.turn.reply import Reaction
from companion.core.types import Json, Speaker, Utterance
from companion.features.reactions.logic import (
    INSTEAD_THRESHOLD,
    InsteadRead,
    is_candidate,
    parse_instead,
    reaction_instead,
    render_reason,
)


def _hist(utterance: Callable[..., Utterance], *pairs: tuple[Speaker, str]) -> list[Utterance]:
    return [utterance(text=t, speaker=s) for s, t in pairs]


C, U = Speaker.COMPANION, Speaker.USER


@pytest.mark.parametrize("text", ["okie :D", "ok", "no", "thanks!", "lol", "yeah"])
def test_a_short_reply_after_a_statement_is_worth_asking_about(
    utterance: Callable[..., Utterance], text: str
) -> None:
    assert is_candidate(text, _hist(utterance, (C, "no rush, tell me later.")))


def test_it_is_only_a_prefilter_so_no_word_list_decides_anything(
    utterance: Callable[..., Utterance],
) -> None:
    # "no" and "yeah" pass the prefilter. The model decides what they mean.
    hist = _hist(utterance, (C, "you should rest."))
    assert is_candidate("no", hist)


@pytest.mark.parametrize(
    ("history", "text"),
    [
        ([(C, "what are you up to?")], "ok"),
        ([], "ok"),
        ([(U, "hey"), (U, "hello")], "ok"),
        ([(C, "go eat.")], "ok?"),
        ([(C, "go eat.")], "ok that makes sense to me now"),
        ([(C, "go eat.")], "x" * 41),
        ([(C, "go eat.")], "   "),
        ([(C, "not explaining the crash 😭")], "😂 fineee"),
        ([(C, "go eat.")], "yesss"),
    ],
)
def test_most_messages_never_reach_the_model(
    utterance: Callable[..., Utterance], history: list[tuple[Speaker, str]], text: str
) -> None:
    assert not is_candidate(text, _hist(utterance, *history))


def test_parse_accepts_a_valid_judgement_and_clamps_confidence() -> None:
    assert parse_instead({"kind": "ack", "confidence": 1.7, "emoji": "👍"}) == InsteadRead(
        "ack", 1.0, "👍"
    )


@pytest.mark.parametrize(
    "data",
    [
        None,
        "ack",
        {"kind": "vibes", "confidence": 0.9, "emoji": "👍"},
        {"kind": "ack", "confidence": "high", "emoji": "👍"},
        {"kind": "ack", "confidence": True, "emoji": "👍"},
        {"kind": "ack", "confidence": 0.9, "emoji": "🦄"},
        {"kind": "ack", "confidence": 0.9},
    ],
)
def test_parse_rejects_anything_off_the_menu(data: Json) -> None:
    assert parse_instead(data) is None


@pytest.mark.parametrize(
    ("kind", "confidence", "reacts"),
    [
        ("ack", 0.95, True),
        ("ack", INSTEAD_THRESHOLD, True),
        ("ack", 0.69, False),
        ("ack", 0.60, False),
        ("answer", 0.99, False),
        ("emotional", 0.99, False),
        ("invitation", 0.99, False),
        ("other", 0.99, False),
    ],
)
def test_only_a_confident_ack_gets_a_reaction(kind: str, confidence: float, reacts: bool) -> None:
    got = reaction_instead(InsteadRead(kind, confidence, "👍"))
    assert (got == Reaction("👍")) is reacts


def test_fine_and_lol_at_seventy_react() -> None:
    assert reaction_instead(InsteadRead("ack", 0.70, "😁")) == Reaction("😁")


def test_the_logged_reason_is_built_from_the_scores() -> None:
    assert render_reason(InsteadRead("ack", 0.93, "❤"), reacted=True) == (
        "reacted ❤ instead of replying: judged ack at 0.93"
    )
    assert "judged emotional at 0.70" in render_reason(InsteadRead("emotional", 0.7, "🤗"), False)
