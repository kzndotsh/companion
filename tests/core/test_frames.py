from __future__ import annotations

from collections.abc import Callable

import pytest

from companion.core.frames import (
    MIN_CONFIDENCE,
    Judgement,
    build_prompt,
    companion_frame,
    has_cue,
    is_assertable,
    needs_judge,
    parse,
    render_reason,
    resolve,
    scene_frame,
    scene_note,
)
from companion.core.types import Belief, Frame, Json, Provenance, Speaker, Utterance


@pytest.mark.parametrize(
    "text",
    [
        "can't we pretend you cooked me lunch",
        "let's pretend you're a pirate",
        "imagine we're on a beach",
        "*hugs you*",
        "what if you could taste food",
        "wanna play a game",
        "let's roleplay",
        "tell me a story",
    ],
)
def test_cues_that_may_mean_play(text: str) -> None:
    assert has_cue(text)


@pytest.mark.parametrize(
    "text", ["i ate a sandwich", "ok i did it, 5 * 3 = 15", "going to bed", "how are you"]
)
def test_ordinary_messages_have_no_cue(text: str) -> None:
    assert not has_cue(text)


def test_a_scene_in_progress_asks_the_judge_even_without_a_cue(
    utterance: Callable[..., Utterance],
) -> None:
    play = [utterance(text="*waves*", speaker=Speaker.USER, frame=Frame.PLAY)]
    assert scene_frame(play) is Frame.PLAY
    assert needs_judge("and then what happens", play)
    assert not needs_judge("and then what happens", [utterance(text="hi")])


def test_stepping_out_ends_the_scene(utterance: Callable[..., Utterance]) -> None:
    out = [
        utterance(text="*waves*", speaker=Speaker.USER, frame=Frame.PLAY),
        utterance(text="wait, seriously though", speaker=Speaker.USER, frame=Frame.OOC),
    ]
    assert scene_frame(out) is Frame.REAL


def test_an_empty_history_is_real() -> None:
    assert scene_frame([]) is Frame.REAL


@pytest.mark.parametrize(
    ("user", "companion"),
    [
        (Frame.PLAY, Frame.PLAY),
        (Frame.STORY, Frame.STORY),
        (Frame.HYPOTHETICAL, Frame.HYPOTHETICAL),
        (Frame.OOC, Frame.REAL),
        (Frame.REAL, Frame.REAL),
    ],
)
def test_the_companion_plays_along_inside_a_scene_only(user: Frame, companion: Frame) -> None:
    assert companion_frame(user) is companion


def test_only_a_scene_gets_a_note() -> None:
    assert scene_note(Frame.PLAY) is not None
    assert scene_note(Frame.STORY) is not None
    assert scene_note(Frame.HYPOTHETICAL) is not None
    assert scene_note(Frame.REAL) is None
    assert scene_note(Frame.OOC) is None


@pytest.mark.parametrize(
    ("data", "frame"),
    [
        ({"frame": "play", "confidence": 0.9}, Frame.PLAY),
        ({"frame": "ooc", "confidence": 1.7}, Frame.OOC),
    ],
)
def test_parse_accepts_a_valid_judgement(data: Json, frame: Frame) -> None:
    got = parse(data)
    assert got is not None
    assert got.frame is frame
    assert 0.0 <= got.confidence <= 1.0


@pytest.mark.parametrize(
    "data",
    [
        None,
        "play",
        {"frame": "dream", "confidence": 0.9},
        {"frame": "play"},
        {"frame": "play", "confidence": True},
        {"frame": 3, "confidence": 0.9},
    ],
)
def test_parse_rejects_anything_off_the_menu(data: Json) -> None:
    assert parse(data) is None


def test_low_confidence_or_missing_falls_back() -> None:
    assert resolve(Judgement(Frame.PLAY, MIN_CONFIDENCE)) is Frame.PLAY
    assert resolve(Judgement(Frame.PLAY, MIN_CONFIDENCE - 0.01)) is Frame.REAL
    assert resolve(None) is Frame.REAL
    assert resolve(None, fallback=Frame.PLAY) is Frame.PLAY
    assert resolve(Judgement(Frame.PLAY, 0.1), fallback=Frame.PLAY) is Frame.PLAY


def test_the_reason_is_built_from_the_scores() -> None:
    assert "judged at 0.90" in render_reason(Judgement(Frame.PLAY, 0.9), Frame.PLAY)
    assert "below 0.70" in render_reason(Judgement(Frame.PLAY, 0.5), Frame.REAL)
    assert "no judgement" in render_reason(None, Frame.REAL)


def test_the_prompt_has_the_last_messages(utterance: Callable[..., Utterance]) -> None:
    hist = [
        utterance(text=f"m{i}", speaker=Speaker.USER if i % 2 else Speaker.COMPANION)
        for i in range(6)
    ]
    prompt = build_prompt(hist, "pretend")
    assert "m1" not in prompt
    assert prompt.endswith("Newest USER message: pretend")


def test_played_and_joked_beliefs_are_never_assertable(belief: Callable[..., Belief]) -> None:
    assert is_assertable(belief(bid="a"))
    assert not is_assertable(belief(bid="b", provenance=Provenance.PLAYED))
    assert not is_assertable(belief(bid="c", provenance=Provenance.JOKED))
    assert not is_assertable(belief(bid="d", provenance=Provenance.HYPOTHETICAL))
    assert is_assertable(belief(bid="e", provenance=Provenance.THIRD_PARTY))
