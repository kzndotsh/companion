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
TEXT = "i have asthma and a bad knee and i've been job hunting for months"


def _candidate(**over: object) -> Candidate:
    base: dict[str, object] = {
        "ref": "m1",
        "quote": "i have asthma and a bad knee",
        "claim": "Has asthma and a bad knee",
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
    assert got.evidence[0].quote == "i have asthma and a bad knee"
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
    assert normalise("Has asthma, and a bad knee.") == normalise("has asthma and a bad knee")


def test_a_momentary_want_is_rejected(utterance: Callable[..., Utterance]) -> None:
    got = _make(
        _candidate(lasting=False, kind=BeliefKind.PREFERENCE, sensitivity=0),
        utterance(text=TEXT, uid="u1"),
    )
    assert isinstance(got, Rejection)
    assert "momentary" in got.reason


@pytest.mark.parametrize(
    ("kind", "sensitivity"),
    [
        (BeliefKind.STATE, 2),
        (BeliefKind.THREAD, 0),
        (BeliefKind.EVENT, 0),
        (BeliefKind.TELL, 1),
        (BeliefKind.TRAIT, 0),
    ],
)
def test_the_momentary_filter_never_drops_these(
    utterance: Callable[..., Utterance], kind: BeliefKind, sensitivity: int
) -> None:
    got = _make(
        _candidate(lasting=False, kind=kind, sensitivity=sensitivity),
        utterance(text=TEXT, uid="u1"),
    )
    assert isinstance(got, Belief)


def test_a_low_confidence_guess_is_rejected(utterance: Callable[..., Utterance]) -> None:
    got = _make(_candidate(confidence=0.3), utterance(text=TEXT, uid="u1"))
    assert isinstance(got, Rejection)


def test_the_prompt_shows_local_weekday_and_date(utterance: Callable[..., Utterance]) -> None:
    from datetime import timedelta, timezone  # noqa: PLC0415

    from companion.core.beliefs.extract import build_user_prompt, index_window  # noqa: PLC0415

    u = utterance(text="i just started working on you last night", uid="u1")
    prompt = build_user_prompt(index_window([u]), {u.id}, {}, timezone(timedelta(hours=-4)))
    assert "Thu 2026-10-01 05:01" in prompt
    assert "UTC" in prompt.splitlines()[0]


def _known(belief: Callable[..., Belief], **over: object) -> dict[str, Belief]:
    return {"k1": belief(bid="b1", **over)}


def test_known_beliefs_get_short_labels_in_the_prompt(
    utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.beliefs.extract import (  # noqa: PLC0415
        build_user_prompt,
        index_window,
        known_index,
    )

    u = utterance(text=TEXT, uid="u1")
    labelled = known_index([belief(bid="b1", claim="Cleans when anxious")])
    prompt = build_user_prompt(index_window([u]), {u.id}, labelled)
    assert "[k1] Cleans when anxious" in prompt


def test_parse_reads_confirms() -> None:
    item: Json = {
        "ref": "m1",
        "quote": "q",
        "claim": "c",
        "subject": "user",
        "kind": "state",
        "provenance": "stated",
        "confidence": 0.5,
        "sensitivity": 0,
        "confirms": " k2 ",
    }
    ok, bad = parse({"beliefs": [item]})
    assert bad == []
    assert ok[0].confirms == "k2"


def test_a_verified_restatement_becomes_a_confirmation(
    utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.beliefs.extract import Confirmation, to_confirmation  # noqa: PLC0415

    new = utterance(text="still so lonely lately", uid="u9")
    c = _candidate(ref="m1", quote="so lonely", confirms="k1")
    got = to_confirmation(c, {"m1": new}, _known(belief))
    assert isinstance(got, Confirmation)
    assert got.evidence.utterance_id == "u9"
    assert got.evidence.quote == "so lonely"


def test_a_confirmation_of_an_unknown_label_is_rejected(
    utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.beliefs.extract import to_confirmation  # noqa: PLC0415

    new = utterance(text="still so lonely", uid="u9")
    got = to_confirmation(_candidate(quote="so lonely", confirms="k9"), {"m1": new}, _known(belief))
    assert isinstance(got, Rejection)


def test_a_confirmation_needs_a_verbatim_quote(
    utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.beliefs.extract import to_confirmation  # noqa: PLC0415

    new = utterance(text="still so lonely", uid="u9")
    got = to_confirmation(
        _candidate(quote="deeply sad", confirms="k1"), {"m1": new}, _known(belief)
    )
    assert isinstance(got, Rejection)
    assert "verbatim" in got.reason


def test_the_same_message_confirming_twice_is_a_skip(
    utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.beliefs.extract import Skip, to_confirmation  # noqa: PLC0415

    same = utterance(text="my studio has never been cleaner, so lonely", uid="u1")
    got = to_confirmation(
        _candidate(quote="so lonely", confirms="k1"), {"m1": same}, _known(belief)
    )
    assert isinstance(got, Skip)


def test_a_restatement_in_a_different_frame_or_by_the_companion_is_rejected(
    utterance: Callable[..., Utterance], belief: Callable[..., Belief]
) -> None:
    from companion.core.beliefs.extract import to_confirmation  # noqa: PLC0415

    play = utterance(text="still so lonely", frame=Frame.PLAY, uid="u8")
    mine = utterance(text="still so lonely", speaker=Speaker.COMPANION, uid="u9")
    known = _known(belief)
    for src in (play, mine):
        got = to_confirmation(_candidate(quote="so lonely", confirms="k1"), {"m1": src}, known)
        assert isinstance(got, Rejection)


@pytest.mark.parametrize(
    ("kind", "provenance"),
    [
        (BeliefKind.TELL, Provenance.INFERRED),
        (BeliefKind.EVENT, Provenance.STATED),
        (BeliefKind.STATE, Provenance.STATED),
        (BeliefKind.TRAIT, Provenance.INFERRED),
        (BeliefKind.PREFERENCE, Provenance.JOKED),
    ],
)
def test_romantic_behaviour_in_the_chat_is_not_a_belief_about_them(
    utterance: Callable[..., Utterance], kind: BeliefKind, provenance: Provenance
) -> None:
    got = _make(
        _candidate(romantic=True, kind=kind, provenance=provenance),
        utterance(text=TEXT, uid="u1"),
    )
    assert isinstance(got, Rejection)
    assert "romantic or sexual" in got.reason


@pytest.mark.parametrize("kind", [BeliefKind.PREFERENCE, BeliefKind.BOUNDARY, BeliefKind.TRAIT])
def test_what_they_plainly_state_about_themselves_there_is_kept(
    utterance: Callable[..., Utterance], kind: BeliefKind
) -> None:
    got = _make(
        _candidate(romantic=True, kind=kind, provenance=Provenance.STATED),
        utterance(text=TEXT, uid="u1"),
    )
    assert isinstance(got, Belief)


def test_an_ordinary_inferred_belief_is_untouched_by_the_romantic_rule(
    utterance: Callable[..., Utterance],
) -> None:
    got = _make(
        _candidate(romantic=False, kind=BeliefKind.TELL, provenance=Provenance.INFERRED),
        utterance(text=TEXT, uid="u1"),
    )
    assert isinstance(got, Belief)
