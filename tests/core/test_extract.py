from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from companion.core.beliefs.extract import (
    Candidate,
    Rejection,
    normalise,
    parse,
    to_belief,
)
from companion.core.types import (
    Belief,
    BeliefKind,
    Frame,
    Json,
    Provenance,
    Speaker,
    Subject,
    Utterance,
)
from tests.conftest import REL

NOW = datetime(2026, 10, 15, 18, 0, tzinfo=UTC)
TEXT = "i have ocd and adhd and i've been job hunting for months"


def _candidate(**over: object) -> Candidate:
    base: dict[str, object] = {
        "ref": "m1",
        "quote": "i have ocd and adhd",
        "claim": "Has OCD and ADHD",
        "subject": Subject.USER,
        "kind": BeliefKind.TRAIT,
        "provenance": Provenance.STATED,
        "confidence": 0.95,
        "sensitivity": 2,
    }
    base.update(over)
    return Candidate(**base)  # type: ignore[arg-type]


def _make(c: Candidate, u: Utterance) -> Belief | Rejection:
    return to_belief(c, {"m1": u}, REL, NOW, lambda: "b1")


def test_a_verbatim_quote_becomes_a_belief(utterance: Callable[..., Utterance]) -> None:
    got = _make(_candidate(), utterance(text=TEXT, uid="u1"))
    assert isinstance(got, Belief)
    assert got.evidence[0].quote == "i have ocd and adhd"
    assert got.speaker is Speaker.USER


def test_single_evidence_confidence_is_capped(utterance: Callable[..., Utterance]) -> None:
    got = _make(_candidate(confidence=0.99), utterance(text=TEXT, uid="u1"))
    assert isinstance(got, Belief)
    assert got.confidence == 0.6


def test_sensitivity_is_clamped(utterance: Callable[..., Utterance]) -> None:
    got = _make(_candidate(sensitivity=9), utterance(text=TEXT, uid="u1"))
    assert isinstance(got, Belief)
    assert got.sensitivity == 3


def test_an_invented_quote_is_rejected(utterance: Callable[..., Utterance]) -> None:
    got = _make(_candidate(quote="i have bipolar disorder"), utterance(text=TEXT, uid="u1"))
    assert isinstance(got, Rejection)
    assert "verbatim" in got.reason


def test_the_companions_words_never_become_user_beliefs(
    utterance: Callable[..., Utterance],
) -> None:
    u = utterance(text="i made you a grilled cheese", speaker=Speaker.COMPANION, uid="u1")
    got = _make(_candidate(quote="i made you a grilled cheese"), u)
    assert isinstance(got, Rejection)
    assert "companion" in got.reason


def test_a_garbled_label_is_rescued_by_the_one_message_that_holds_the_quote(
    utterance: Callable[..., Utterance],
) -> None:
    got = _make(_candidate(ref="44448 4bb8"), utterance(text=TEXT, uid="u1"))
    assert isinstance(got, Belief)
    assert got.evidence[0].utterance_id == "u1"


def test_a_garbled_label_with_a_bad_quote_is_still_rejected(
    utterance: Callable[..., Utterance],
) -> None:
    got = _make(_candidate(ref="zz", quote="i have bipolar"), utterance(text=TEXT, uid="u1"))
    assert isinstance(got, Rejection)


def test_a_garbled_label_is_rejected_when_two_messages_hold_the_quote(
    utterance: Callable[..., Utterance],
) -> None:
    one, two = utterance(text=TEXT, uid="u1"), utterance(text=TEXT, uid="u2")
    got = to_belief(_candidate(ref="??"), {"m1": one, "m2": two}, REL, NOW, lambda: "b")
    assert isinstance(got, Rejection)


def test_the_label_can_not_point_at_the_companions_words(
    utterance: Callable[..., Utterance],
) -> None:
    mine = utterance(text=TEXT, speaker=Speaker.COMPANION, uid="u1")
    assert isinstance(_make(_candidate(ref="m1"), mine), Rejection)


def test_the_model_cannot_claim_companion_said(utterance: Callable[..., Utterance]) -> None:
    got = _make(_candidate(provenance=Provenance.COMPANION_SAID), utterance(text=TEXT, uid="u1"))
    assert isinstance(got, Rejection)


def test_sincere_provenance_in_a_play_frame_is_rejected(
    utterance: Callable[..., Utterance],
) -> None:
    got = _make(_candidate(), utterance(text=TEXT, frame=Frame.PLAY, uid="u1"))
    assert isinstance(got, Rejection)
    assert "invariant" in got.reason


def test_parse_accepts_a_well_formed_response() -> None:
    data: Json = {
        "beliefs": [
            {
                "ref": "m1",
                "quote": "q",
                "claim": " c ",
                "subject": "user",
                "kind": "trait",
                "provenance": "stated",
                "confidence": 0.5,
                "sensitivity": 1,
            }
        ]
    }
    ok, bad = parse(data)
    assert len(ok) == 1
    assert ok[0].claim == "c"
    assert bad == []


@pytest.mark.parametrize(
    "data",
    [None, "text", [], {"beliefs": "no"}, {}],
)
def test_parse_rejects_a_malformed_whole(data: Json) -> None:
    ok, bad = parse(data)
    assert ok == []
    assert len(bad) == 1


def test_parse_keeps_good_items_and_rejects_bad_ones() -> None:
    good: Json = {
        "ref": "m1",
        "quote": "q",
        "claim": "c",
        "subject": "user",
        "kind": "trait",
        "provenance": "stated",
        "confidence": 0.5,
        "sensitivity": 0,
    }
    ok, bad = parse({"beliefs": [good, {**good, "kind": "vibes"}, {**good, "confidence": "high"}]})
    assert len(ok) == 1
    assert len(bad) == 2


def test_normalise_ignores_case_and_punctuation() -> None:
    assert normalise("Has OCD, and ADHD.") == normalise("has ocd and adhd")
