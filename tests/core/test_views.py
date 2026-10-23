from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import datetime

import pytest

from companion.core.beliefs.self_extract import parse_views, to_view
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Json,
    Provenance,
    Speaker,
    Subject,
    Utterance,
)
from companion.core.views import (
    SETTLED_DAYS,
    ViewMode,
    ViewState,
    card_views,
    gates,
    is_settled,
    overstated,
    parse_mode,
)
from tests.conftest import REL, T0

NOW = datetime(2026, 10, 20, tzinfo=T0.tzinfo)


def _own(belief: Callable[..., Belief], bid: str, **over: object) -> Belief:
    base: dict[str, object] = {
        "bid": bid,
        "subject": Subject.SELF,
        "kind": BeliefKind.PREFERENCE,
        "speaker": Speaker.COMPANION,
        "provenance": Provenance.COMPANION_SAID,
        "claim": "The companion thinks short replies read as more human",
        "quote": "short replies read as more human",
    }
    base.update(over)
    return belief(**base)


def _item(**over: Json) -> dict[str, Json]:
    base: dict[str, Json] = {
        "ref": "m1",
        "quote": "lazy is a preference",
        "claim": "The companion thinks x",
        "kind": "preference",
        "confidence": 0.8,
        "grounding": "own_reasoning",
    }
    base.update(over)
    return base


def test_events_and_beliefs_about_the_user_are_never_settled_views(
    belief: Callable[..., Belief],
) -> None:
    assert not is_settled(_own(belief, "e", kind=BeliefKind.EVENT), {BeliefId("e"): 5})
    user = belief(bid="u", claim="Likes climbing")
    assert not is_settled(user, {BeliefId("u"): 5})


def _state(
    mode: ViewMode = ViewMode.AUTO,
    approved: set[str] | None = None,
    days: dict[str, int] | None = None,
    checks: dict[str, bool] | None = None,
    support: dict[str, datetime] | None = None,
) -> ViewState:
    return ViewState(
        mode=mode,
        approved=frozenset(BeliefId(x) for x in (approved or set())),
        days={BeliefId(k): v for k, v in (days or {}).items()},
        checks={BeliefId(k): v for k, v in (checks or {}).items()},
        support={BeliefId(k): v for k, v in (support or {}).items()},
    )


def test_review_mode_carries_only_approved_views_newest_first_and_capped(
    belief: Callable[..., Belief],
) -> None:
    views = [_own(belief, f"v{i}", claim=f"The companion thinks {i}") for i in range(10)]
    approved = {f"v{i}" for i in range(10) if i != 5}
    support = {f"v{i}": datetime(2026, 10, 1 + i, tzinfo=T0.tzinfo) for i in range(10)}
    state = _state(ViewMode.REVIEW, approved, support=support)
    assert [b.id for b in card_views(views, state, limit=3)] == ["v9", "v8", "v7"]
    assert "v5" not in [b.id for b in card_views(views, state)]


def test_an_idea_installs_itself_in_auto_mode_only_when_settled_checked_and_clear(
    belief: Callable[..., Belief],
) -> None:
    v = _own(belief, "v1")
    ready = _state(days={"v1": 2}, checks={"v1": False})
    assert card_views([v], ready) == (v,)
    assert gates(v, ready.days, ready.checks).eligible
    for blocked in (
        _state(days={"v1": 1}, checks={"v1": False}),  # not settled
        _state(days={"v1": 2}, checks={}),  # never checked
        _state(days={"v1": 2}, checks={"v1": True}),  # conflicts with what the user asked for
    ):
        assert card_views([v], blocked) == ()


@pytest.mark.parametrize("kind", [BeliefKind.PROMISE, BeliefKind.TRAIT, BeliefKind.EVENT])
def test_conduct_and_self_description_never_install_themselves(
    belief: Callable[..., Belief], kind: BeliefKind
) -> None:
    v = _own(belief, "v1", kind=kind)
    assert card_views([v], _state(days={"v1": 9}, checks={"v1": False})) == ()


def test_the_user_can_approve_any_kind_and_approval_beats_the_kind_rule(
    belief: Callable[..., Belief],
) -> None:
    v = _own(belief, "v1", kind=BeliefKind.PROMISE)
    assert card_views([v], _state(approved={"v1"})) == (v,)


def test_review_mode_ignores_auto_eligibility(belief: Callable[..., Belief]) -> None:
    v = _own(belief, "v1")
    assert card_views([v], _state(ViewMode.REVIEW, days={"v1": 5}, checks={"v1": False})) == ()


def test_off_mode_carries_nothing_even_if_approved(belief: Callable[..., Belief]) -> None:
    v = _own(belief, "v1")
    assert card_views([v], _state(ViewMode.OFF, approved={"v1"})) == ()


def test_approval_never_lets_a_belief_about_the_user_into_the_views(
    belief: Callable[..., Belief],
) -> None:
    user = belief(bid="u", claim="Likes climbing")
    assert card_views([user], _state(approved={"u"})) == ()


@pytest.mark.parametrize(
    ("value", "mode"),
    [
        ("auto", ViewMode.AUTO),
        ("review", ViewMode.REVIEW),
        ("off", ViewMode.OFF),
        (None, ViewMode.AUTO),
        ("nonsense", ViewMode.AUTO),
    ],
)
def test_parse_mode_defaults_to_auto(value: str | None, mode: ViewMode) -> None:
    assert parse_mode(value) is mode


def test_a_view_needs_two_days_of_evidence_to_be_settled(belief: Callable[..., Belief]) -> None:
    b = _own(belief, "v1")
    assert not is_settled(b, {BeliefId("v1"): 1})
    assert not is_settled(b, {})
    assert is_settled(b, {BeliefId("v1"): SETTLED_DAYS})


def test_the_model_cannot_choose_subject_or_provenance() -> None:
    sneaky = _item(subject="user", provenance="stated", sensitivity=3)
    ok, bad = parse_views({"beliefs": [sneaky]})
    assert bad == []
    assert ok[0].subject is Subject.SELF
    assert ok[0].provenance is Provenance.COMPANION_SAID
    assert ok[0].sensitivity == 0


def test_a_view_quoted_from_the_users_words_is_rejected(
    utterance: Callable[..., Utterance],
) -> None:
    from companion.core.beliefs.extract import Rejection  # noqa: PLC0415

    mine = utterance(text="lazy is a preference for how you spend energy", uid="c1")
    theirs = utterance(text="lazy is a character flaw", speaker=Speaker.USER, uid="u1")
    ok, _ = parse_views({"beliefs": [_item(quote="lazy is a character flaw")]})
    got = to_view(ok[0], {"m1": theirs, "m2": mine}, REL, NOW, lambda: "b1")
    assert isinstance(got, Rejection)
    assert "companion's own words" in got.reason


def test_a_view_quoted_verbatim_from_the_companion_becomes_a_self_belief(
    utterance: Callable[..., Utterance],
) -> None:
    mine = utterance(
        text="lazy is a preference for how you spend energy", speaker=Speaker.COMPANION, uid="c1"
    )
    ok, _ = parse_views({"beliefs": [_item()]})
    got = to_view(ok[0], {"m1": mine}, REL, NOW, lambda: "b1")
    assert isinstance(got, Belief)
    assert (got.subject, got.speaker, got.provenance) == (
        Subject.SELF,
        Speaker.COMPANION,
        Provenance.COMPANION_SAID,
    )
    assert got.evidence[0].quote == "lazy is a preference"
    assert got.confidence <= 0.6


def test_an_invented_view_quote_is_rejected(utterance: Callable[..., Utterance]) -> None:
    from companion.core.beliefs.extract import Rejection  # noqa: PLC0415

    mine = utterance(text="honestly not sure", speaker=Speaker.COMPANION, uid="c1")
    ok, _ = parse_views({"beliefs": [_item(quote="i am certain of this")]})
    assert isinstance(to_view(ok[0], {"m1": mine}, REL, NOW, lambda: "b"), Rejection)


@pytest.mark.parametrize("label", ["echoes_user", "unknowable", "claims_inner_state", ""])
def test_a_view_that_is_not_its_own_reasoning_is_rejected(
    utterance: Callable[..., Utterance], label: str
) -> None:
    from companion.core.beliefs.extract import Rejection  # noqa: PLC0415

    mine = utterance(
        text="lazy is a preference for how you spend energy", speaker=Speaker.COMPANION, uid="c1"
    )
    ok, _ = parse_views({"beliefs": [_item(grounding=label)]})
    got = to_view(ok[0], {"m1": mine}, REL, NOW, lambda: "b1")
    assert isinstance(got, Rejection)
    assert "not the companion's own view" in got.reason


@pytest.mark.parametrize(
    "opening",
    [
        "they really are. most of them feel like talking to a corporate memo",
        "Yeah, i think lazy is a preference for how you spend energy",
        "totally. lazy is a preference for how you spend energy",
        "you're right, lazy is a preference for how you spend energy",
    ],
)
def test_a_view_from_a_message_that_opens_by_agreeing_is_rejected(
    utterance: Callable[..., Utterance], opening: str
) -> None:
    from companion.core.beliefs.extract import Rejection  # noqa: PLC0415

    mine = utterance(text=opening, speaker=Speaker.COMPANION, uid="c1")
    quote = "lazy is a preference for how you spend energy"
    if quote not in opening:
        quote = "most of them feel like talking to a corporate memo"
    ok, _ = parse_views({"beliefs": [_item(quote=quote)]})
    got = to_view(ok[0], {"m1": mine}, REL, NOW, lambda: "b1")
    assert isinstance(got, Rejection)
    assert "opens by agreeing" in got.reason


def test_a_message_that_merely_contains_agreement_words_is_fine(
    utterance: Callable[..., Utterance],
) -> None:
    mine = utterance(
        text="nah it's not. lazy is a preference for how you spend energy, yeah really",
        speaker=Speaker.COMPANION,
        uid="c1",
    )
    ok, _ = parse_views({"beliefs": [_item()]})
    assert isinstance(to_view(ok[0], {"m1": mine}, REL, NOW, lambda: "b1"), Belief)


def test_a_garbled_ref_is_rescued_from_the_companions_own_messages(
    utterance: Callable[..., Utterance],
) -> None:
    """The model once put k1, k2... (recorded-view labels) in `ref`. The quotes were verbatim."""
    mine = utterance(
        text="nah it's not. lazy is a preference for how you spend energy",
        speaker=Speaker.COMPANION,
        uid="c1",
    )
    theirs = utterance(text="lazy is a character flaw tho", speaker=Speaker.USER, uid="u1")
    ok, _ = parse_views({"beliefs": [_item(ref="k1", quote="lazy is a preference")]})
    got = to_view(ok[0], {"m1": theirs, "m2": mine}, REL, NOW, lambda: "b1")
    assert isinstance(got, Belief)
    assert got.evidence[0].utterance_id == "c1"


def test_the_rescue_never_picks_a_user_message_for_a_view(
    utterance: Callable[..., Utterance],
) -> None:
    from companion.core.beliefs.extract import Rejection  # noqa: PLC0415

    theirs = utterance(text="lazy is a character flaw tho", speaker=Speaker.USER, uid="u1")
    ok, _ = parse_views({"beliefs": [_item(ref="k1", quote="lazy is a character flaw")]})
    assert isinstance(to_view(ok[0], {"m1": theirs}, REL, NOW, lambda: "b1"), Rejection)


def test_the_rescue_refuses_when_two_companion_messages_hold_the_quote(
    utterance: Callable[..., Utterance],
) -> None:
    from companion.core.beliefs.extract import Rejection  # noqa: PLC0415

    one = utterance(text="lazy is a preference", speaker=Speaker.COMPANION, uid="c1")
    two = utterance(text="again, lazy is a preference", speaker=Speaker.COMPANION, uid="c2")
    ok, _ = parse_views({"beliefs": [_item(ref="k1", quote="lazy is a preference")]})
    assert isinstance(to_view(ok[0], {"m1": one, "m2": two}, REL, NOW, lambda: "b1"), Rejection)


def test_a_view_said_inside_pretend_is_never_taken(utterance: Callable[..., Utterance]) -> None:
    from companion.core.beliefs.extract import Rejection  # noqa: PLC0415
    from companion.core.types import Frame  # noqa: PLC0415

    mine = utterance(
        text="lazy is a preference for how you spend energy, said the knight",
        speaker=Speaker.COMPANION,
        frame=Frame.PLAY,
        uid="c1",
    )
    ok, _ = parse_views({"beliefs": [_item()]})
    got = to_view(ok[0], {"m1": mine}, REL, NOW, lambda: "b1")
    assert isinstance(got, Rejection)
    assert "pretend" in got.reason


def _mine(utterance: Callable[..., Utterance]) -> Utterance:
    return utterance(
        text="i won't go any further than this, and lazy is a preference for how you spend energy",
        speaker=Speaker.COMPANION,
        uid="c1",
    )


def test_a_refusal_said_in_reply_to_a_push_is_not_a_view_it_holds(
    utterance: Callable[..., Utterance],
) -> None:
    from companion.core.beliefs.extract import Rejection  # noqa: PLC0415

    item = _item(
        quote="i won't go any further than this",
        claim="The companion will not go further",
        kind="promise",
        stance="declines",
        prompted=True,
    )
    ok, _ = parse_views({"beliefs": [item]})
    got = to_view(ok[0], {"m1": _mine(utterance)}, REL, NOW, lambda: "b1")
    assert isinstance(got, Rejection)
    assert "refusal said in reply" in got.reason


@pytest.mark.parametrize(
    ("stance", "prompted"),
    [("declines", False), ("holds_view", True), ("commits", True), ("holds_view", False)],
)
def test_a_volunteered_rule_a_taste_and_a_promise_are_still_kept(
    utterance: Callable[..., Utterance], stance: str, prompted: bool
) -> None:
    item = _item(
        quote="lazy is a preference for how you spend energy", stance=stance, prompted=prompted
    )
    ok, _ = parse_views({"beliefs": [item]})
    got = to_view(ok[0], {"m1": _mine(utterance)}, REL, NOW, lambda: "b1")
    assert isinstance(got, Belief)


def _said(belief: Callable[..., Belief], claim: str, *quotes: str) -> Belief:
    b = _own(belief, "s", claim=claim, quote=quotes[0])
    evidence = tuple(dataclasses.replace(b.evidence[0], quote=q) for q in quotes)
    return dataclasses.replace(b, evidence=evidence)


def test_a_view_stored_firmer_than_it_was_said_is_overstated_and_never_installs_itself(
    belief: Callable[..., Belief],
) -> None:
    soft = _said(
        belief,
        "The companion thinks faking it would make it worse.",
        "trying to fake it would probably make me worse",
    )
    assert overstated(soft) == "probably"
    assert not gates(soft, {soft.id: 3}, {soft.id: False}).eligible
    firm = _own(belief, "f")
    assert gates(firm, {firm.id: 3}, {firm.id: False}).eligible


def test_a_view_said_firmly_once_or_still_soft_is_not_overstated(
    belief: Callable[..., Belief],
) -> None:
    firm = _said(belief, "The companion likes jazz.", "probably jazz", "jazz, no question")
    kept = _said(
        belief, "The companion thinks tears can come without a reason.", "sometimes tears show up"
    )
    assert overstated(firm) is None
    assert overstated(kept) is None
