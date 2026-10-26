from __future__ import annotations

from collections.abc import Callable

import pytest

from companion.core.types import Frame, Speaker, Utterance
from companion.features.history.logic import (
    CanonRead,
    Proposed,
    Standing,
    Story,
    StoryId,
    Verdict,
    parse_canon,
    rule,
    to_story,
)

PET = StoryId("pet00000aaaa")
CLAIMS = {PET: "The companion once had a cat called Pebble."}
SAID = "lol this is like the time i named a stray cat pebble and it never came back"


def _reads(*verdicts: Verdict, of: StoryId | None = None) -> list[CanonRead | None]:
    return [
        CanonRead(v, of if v in {Verdict.SAME, Verdict.CONTRADICTS} else None) for v in verdicts
    ]


@pytest.mark.parametrize(
    ("reads", "standing", "of", "reason"),
    [
        (_reads(Verdict.FITS, Verdict.FITS, Verdict.FITS), Standing.CANON, None, "fits"),
        (_reads(Verdict.SAME, Verdict.SAME, Verdict.FITS, of=PET), Standing.EVIDENCE, PET, "same"),
        (_reads(Verdict.SAME, Verdict.FITS, Verdict.FITS, of=PET), Standing.CANON, None, "fits"),
        (
            _reads(Verdict.CONTRADICTS, Verdict.CONTRADICTS, Verdict.FITS, of=PET),
            Standing.NOT_CANON,
            PET,
            'contradicts pet00000 ("The companion once had a cat called Pebble.")',
        ),
        (
            _reads(Verdict.CONTRADICTS, Verdict.CONTRADICTS, Verdict.CONTRADICTS),
            Standing.NOT_CANON,
            None,
            "contradicts the character sheet",
        ),
        (
            _reads(Verdict.FITS, Verdict.FITS, Verdict.TOO_BIG),
            Standing.NOT_CANON,
            None,
            "a big life event the character sheet does not have",
        ),
        (
            _reads(Verdict.NOT_A_STORY, Verdict.NOT_A_STORY, Verdict.TOO_BIG),
            Standing.NOT_CANON,
            None,
            "not a story about its own past",
        ),
    ],
)
def test_each_set_of_reads_becomes_one_standing_with_a_code_written_reason(
    reads: list[CanonRead | None], standing: Standing, of: StoryId | None, reason: str
) -> None:
    got = rule(reads, CLAIMS)
    assert got is not None
    assert (got.standing, got.of) == (standing, of)
    assert reason in got.reason


def test_a_failed_read_rules_nothing() -> None:
    assert rule([*_reads(Verdict.FITS, Verdict.FITS), None], CLAIMS) is None
    assert rule([], CLAIMS) is None


def test_same_without_a_kept_story_is_unreadable_and_contradicts_may_name_the_sheet() -> None:
    refs = {"s1": PET}
    assert parse_canon({"verdict": "same", "story": "s9"}, refs) is None
    assert parse_canon({"verdict": "same", "story": "[s1]"}, refs) == CanonRead(Verdict.SAME, PET)
    assert parse_canon({"verdict": "contradicts", "story": ""}, refs) == CanonRead(
        Verdict.CONTRADICTS, None
    )
    assert parse_canon({"verdict": "fits", "story": "s1"}, refs) == CanonRead(Verdict.FITS, None)
    assert parse_canon({"verdict": "maybe", "story": ""}, refs) is None


def _story(
    utterance: Callable[..., Utterance], frame: Frame, place: str, speaker: Speaker
) -> Story | str:
    u = utterance(text=SAID, speaker=speaker, frame=frame)
    p = Proposed(
        "m1", "i named a stray cat pebble", "The companion named a stray cat Pebble.", place
    )
    return to_story(p, {"m1": u}, "x")


def test_a_passing_fact_in_a_scene_is_kept_with_its_frame_and_a_scene_event_is_not(
    utterance: Callable[..., Utterance],
) -> None:
    kept = _story(utterance, Frame.PLAY, "its_past", Speaker.COMPANION)
    assert isinstance(kept, Story)
    assert (kept.frame, kept.quote) == (Frame.PLAY, "i named a stray cat pebble")
    assert _story(utterance, Frame.PLAY, "scene", Speaker.COMPANION) == (
        "something that happens in the scene, not its own past"
    )
    assert _story(utterance, Frame.HYPOTHETICAL, "its_past", Speaker.COMPANION) == (
        "said in a what-if"
    )
    assert _story(utterance, Frame.REAL, "its_past", Speaker.USER) == "not one of its own messages"


def test_a_quote_not_in_its_message_is_dropped(utterance: Callable[..., Utterance]) -> None:
    u = utterance(text=SAID, speaker=Speaker.COMPANION)
    p = Proposed("m1", "i had a dog named rex", "The companion had a dog.", "its_past")
    assert to_story(p, {"m1": u}, "x") == "quote not in the message"
