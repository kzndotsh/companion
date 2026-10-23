from __future__ import annotations

import pytest

from companion.core.turn.react import MIN_CONFIDENCE, MIN_GAP, Judgement, decide, parse


def _j(tone: str = "funny", confidence: float = 0.9, emoji: str = "😁") -> Judgement:
    return Judgement(tone, confidence, emoji)


def test_a_clear_confident_tone_with_no_recent_reaction_reacts() -> None:
    d = decide(_j(), None)
    assert d.reaction is not None
    assert d.reaction.emoji == "😁"
    assert "alongside the reply" in d.reason


def test_a_plain_message_gets_no_reaction() -> None:
    d = decide(_j("plain", 0.99), None)
    assert d.reaction is None
    assert "plain" in d.reason


def test_a_hesitant_judgement_gets_no_reaction() -> None:
    d = decide(_j(confidence=MIN_CONFIDENCE - 0.01), None)
    assert d.reaction is None
    assert "needs" in d.reason


@pytest.mark.parametrize(("since", "reacts"), [(0, False), (MIN_GAP - 1, False), (MIN_GAP, True)])
def test_a_reaction_is_not_repeated_too_soon(since: int, reacts: bool) -> None:
    d = decide(_j(), since)
    assert (d.reaction is not None) is reacts
    if not reacts:
        assert "last reaction" in d.reason


def test_parse_accepts_a_well_formed_answer_and_clamps_confidence() -> None:
    got = parse({"tone": "sweet", "confidence": 1.7, "emoji": "❤"})
    assert got == Judgement("sweet", 1.0, "❤")


@pytest.mark.parametrize(
    "data",
    [
        None,
        "x",
        {"tone": "silly", "confidence": 0.9, "emoji": "😁"},
        {"tone": "funny", "confidence": True, "emoji": "😁"},
        {"tone": "funny", "confidence": 0.9, "emoji": "💩"},
        {"tone": "funny", "confidence": "high", "emoji": "😁"},
    ],
)
def test_parse_rejects_anything_malformed(data: object) -> None:
    assert parse(data) is None  # type: ignore[arg-type]


def test_a_heavy_message_never_gets_a_reaction_however_sure_the_judge_is() -> None:
    d = decide(_j("sad", 0.99, "🤗"), None)
    assert d.reaction is None
    assert "too heavy" in d.reason
