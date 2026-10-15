from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    DecisionKind,
    Evidence,
    Frame,
    Json,
    Provenance,
    RelationshipId,
    SessionId,
    Speaker,
    Subject,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.core.views import card_views, is_settled
from companion.loops.curate import rebuild, retire_implicated_views
from companion.loops.fast import Conversation
from companion.loops.slow import reflect_once
from companion.loops.views import check_views, views_implicated
from companion.store.sqlite import replay as store_replay
from companion.store.sqlite.store import VIEWS_MODE_KEY, Store

REL = RelationshipId("rel")
T0 = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
PREFIX = build_prefix("You are steady and warm. " * 200)
VIEW_TEXT = "i don't think lazy is a flaw, it's a preference for how you spend energy"


class Routed:
    """Answers the user pass and the self pass separately, and records every prompt."""

    def __init__(
        self,
        users: list[Json] | None = None,
        views: list[Json] | None = None,
        checks: list[Json] | None = None,
        implications: list[Json] | None = None,
    ) -> None:
        self.users = list(users or [])
        self.views = list(views or [])
        self.checks = list(checks or [])
        self.implications = list(implications or [])
        self.prompts: dict[str, list[str]] = {"user": [], "self": [], "check": [], "flag": []}

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        if "flagged a reply from their companion as wrong" in system:
            which, queue = "flag", self.implications
        elif "compare views that a companion holds" in system:
            which, queue = "check", self.checks
        elif "views the COMPANION expressed" in system:
            which, queue = "self", self.views
        else:
            which, queue = "user", self.users
        self.prompts[which].append(user)
        data: Json = queue.pop(0) if queue else {"beliefs": []}
        return Extraction(data, "fake", 0.0, 1)


def _say(store: Store, n: int, speaker: Speaker, text: str) -> Utterance:
    u = Utterance(
        UtteranceId(f"u{n}"),
        REL,
        SessionId("s"),
        TurnId(f"t{n}"),
        speaker,
        text,
        Frame.REAL,
        "test",
        T0 + timedelta(minutes=n),
    )
    store.append_utterance(u)
    return u


def _view(
    ref: str, quote: str, claim: str = "The companion thinks laziness is not a flaw."
) -> Json:
    return {
        "beliefs": [
            {
                "ref": ref,
                "quote": quote,
                "claim": claim,
                "kind": "preference",
                "confidence": 0.8,
                "grounding": "own_reasoning",
            }
        ]
    }


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def test_a_view_is_recorded_from_the_companions_own_words(store: Store) -> None:
    _say(store, 1, Speaker.USER, "lazy is a character flaw tho")
    _say(store, 2, Speaker.COMPANION, VIEW_TEXT)
    ex = Routed(views=[_view("m2", "lazy is a flaw")])
    result = await reflect_once(store, ex, REL)
    assert (result.views_accepted, result.views_rejected) == (1, 0)
    [v] = store.self_beliefs(REL)
    assert (v.subject, v.speaker, v.provenance) == (
        Subject.SELF,
        Speaker.COMPANION,
        Provenance.COMPANION_SAID,
    )
    assert v.evidence[0].utterance_id == "u2"
    assert store.user_beliefs(REL) == []


async def test_a_view_cannot_be_quoted_from_the_users_message(store: Store) -> None:
    _say(store, 1, Speaker.USER, "lazy is a character flaw tho")
    _say(store, 2, Speaker.COMPANION, VIEW_TEXT)
    ex = Routed(views=[_view("m1", "lazy is a character flaw")])
    result = await reflect_once(store, ex, REL)
    assert (result.views_accepted, result.views_rejected) == (0, 1)
    assert store.self_beliefs(REL) == []


async def test_the_user_pass_never_sees_the_companions_views(store: Store) -> None:
    _say(store, 1, Speaker.COMPANION, VIEW_TEXT)
    await reflect_once(store, Routed(views=[_view("m1", "lazy is a flaw")]), REL)
    _say(store, 2, Speaker.USER, "i like climbing")
    spy = Routed()
    await reflect_once(store, spy, REL)
    assert "laziness" not in spy.prompts["user"][0]


async def test_a_view_is_tentative_until_restated_on_another_day(store: Store) -> None:
    _say(store, 1, Speaker.COMPANION, VIEW_TEXT)
    await reflect_once(store, Routed(views=[_view("m1", "lazy is a flaw")]), REL)
    [v] = store.self_beliefs(REL)
    assert not is_settled(v, store.evidence_days(REL))

    _say(store, 60 * 30, Speaker.COMPANION, "still think lazy is a flaw? no. it's about energy")
    restated: Json = {
        "beliefs": [
            {
                "ref": "m2",
                "quote": "it's about energy",
                "kind": "preference",
                "confidence": 0.8,
                "grounding": "own_reasoning",
                "claim": "The companion thinks laziness is not a flaw.",
                "confirms": "k1",
            }
        ]
    }
    result = await reflect_once(store, Routed(views=[restated]), REL)
    assert result.views_confirmed == 1
    assert len(store.self_beliefs(REL)) == 1
    assert is_settled(store.self_beliefs(REL)[0], store.evidence_days(REL))
    assert card_views(store.self_beliefs(REL), store.view_state(REL)) == ()  # unchecked


async def test_a_rebuild_restates_the_user_beliefs_and_leaves_the_views_alone(
    store: Store,
) -> None:
    _say(store, 1, Speaker.USER, "i like climbing")
    _say(store, 2, Speaker.COMPANION, VIEW_TEXT)
    user_item: Json = {
        "beliefs": [
            {
                "ref": "m1",
                "quote": "i like climbing",
                "claim": "Likes climbing.",
                "subject": "user",
                "kind": "preference",
                "provenance": "stated",
                "confidence": 0.9,
                "lasting": True,
                "sensitivity": 0,
            }
        ]
    }
    await reflect_once(store, Routed([user_item], [_view("m2", "lazy is a flaw")]), REL)
    view_id = store.self_beliefs(REL)[0].id
    await rebuild(store, Routed([user_item], []), REL)
    assert [b.id for b in store.self_beliefs(REL)] == [view_id]
    assert len(store.user_beliefs(REL)) == 1


class _Talker:
    def __init__(self) -> None:
        self.seen: list[TalkerRequest] = []

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        return Reply("ok", "m", 5)


def _own_view(bid: str, uid: str, quote: str, claim: str) -> Belief:
    return Belief(
        id=BeliefId(bid),
        relationship_id=REL,
        subject=Subject.SELF,
        kind=BeliefKind.PREFERENCE,
        claim=claim,
        evidence=(Evidence(UtteranceId(uid), quote),),
        provenance=Provenance.COMPANION_SAID,
        speaker=Speaker.COMPANION,
        frame=Frame.REAL,
        confidence=0.6,
        valid_from=T0,
        recorded_at=T0,
    )


async def test_only_approved_views_reach_the_model_and_the_placement_is_logged(
    store: Store, tmp_path: Path
) -> None:
    _say(store, 1, Speaker.COMPANION, "short replies read as more human to me")
    _say(store, 60 * 30, Speaker.COMPANION, "yeah, short replies read as more human, i stand by it")
    _say(store, 3, Speaker.COMPANION, "pineapple on pizza is fine")
    _say(store, 4, Speaker.COMPANION, "i will never pretend to have hands")
    settled_but_unapproved = _own_view(
        "settled",
        "u1",
        "short replies read as more human",
        "The companion thinks short replies read as more human.",
    )
    store.insert_belief(settled_but_unapproved)
    store.add_evidence(
        settled_but_unapproved.id,
        Evidence(UtteranceId(f"u{60 * 30}"), "short replies read as more human"),
    )
    approved_once = _own_view(
        "approved",
        "u3",
        "pineapple on pizza is fine",
        "The companion thinks pineapple on pizza is fine.",
    )
    store.insert_belief(approved_once)
    store.approve_view(approved_once.id, T0)
    closed = _own_view(
        "closed",
        "u4",
        "i will never pretend to have hands",
        "The companion will never pretend to have hands.",
    )
    store.insert_belief(closed)
    store.approve_view(closed.id, T0)
    store.close_belief(closed.id, T0 + timedelta(days=1))
    talker = _Talker()
    await Conversation(store, talker, PREFIX, REL).handle(
        SessionId("s"), "hi", "test", T0 + timedelta(days=3)
    )
    sent = talker.seen[0].messages[-1].content
    assert "[Views of your own that you have expressed and they have approved" in sent
    assert "pineapple on pizza is fine" in sent
    assert "short replies read as more human" not in sent  # settled, but not approved
    assert "pretend to have hands" not in sent  # approved, then closed
    store.close()
    db = tmp_path / "rel.sqlite"
    import sqlite3  # noqa: PLC0415

    with sqlite3.connect(db) as c:
        turn = str(c.execute("SELECT turn_id FROM turn_requests").fetchone()[0])
    report = store_replay.replay_file(db, turn)
    assert report.matched
    reasons = {str(d.belief_id): (d.kind, d.reason) for d in report.decisions if d.belief_id}
    assert reasons["approved"] == (
        DecisionKind.SURFACE,
        "in the card as a view of its own that the user approved",
    )
    assert "settled" not in reasons
    assert "closed" not in reasons


def _two_day_view(
    store: Store, bid: str = "idea", kind: BeliefKind = BeliefKind.PREFERENCE
) -> Belief:
    _say(store, 1, Speaker.COMPANION, "short replies read as more human to me")
    _say(store, 60 * 30, Speaker.COMPANION, "still: short replies read as more human")
    view = _own_view(
        bid,
        "u1",
        "short replies read as more human",
        "The companion thinks short replies read as more human.",
    )
    view = Belief(**{**view.__dict__, "kind": kind}) if False else view
    store.insert_belief(view)
    store.add_evidence(
        view.id, Evidence(UtteranceId(f"u{60 * 30}"), "short replies read as more human")
    )
    return view


def _verdict(conflicts: bool, with_label: str = "") -> Json:
    return {
        "results": [{"view": "v1", "conflicts": conflicts, "with": with_label, "confidence": 0.9}]
    }


async def test_a_settled_idea_is_checked_once_and_then_installs_itself(store: Store) -> None:
    _two_day_view(store)
    assert card_views(store.self_beliefs(REL), store.view_state(REL)) == ()  # unchecked
    ex = Routed(checks=[_verdict(False)])
    result = await check_views(store, ex, REL)
    assert (result.checked, result.conflicts) == (1, 0)
    assert [b.id for b in card_views(store.self_beliefs(REL), store.view_state(REL))] == ["idea"]
    again = await check_views(store, ex, REL)
    assert again.checked == 0  # already checked, so no second model call
    assert len(ex.prompts["check"]) == 1


async def test_a_view_that_conflicts_with_what_the_user_asked_for_stays_out(store: Store) -> None:
    _say(store, 5, Speaker.USER, "i'm fine with pretending, it's not annoying to me")
    wants: Json = {
        "beliefs": [
            {
                "ref": "m1",
                "quote": "i'm fine with pretending",
                "claim": "The user is fine with pretend play.",
                "subject": "user",
                "kind": "preference",
                "provenance": "stated",
                "confidence": 0.9,
                "lasting": True,
                "sensitivity": 0,
            }
        ]
    }
    await reflect_once(store, Routed(users=[wants]), REL)
    _two_day_view(store)
    ex = Routed(checks=[_verdict(True, "k1")])
    result = await check_views(store, ex, REL)
    assert result.conflicts == 1
    assert "The user is fine with pretend play." in ex.prompts["check"][0]
    assert card_views(store.self_beliefs(REL), store.view_state(REL)) == ()


async def test_a_new_user_preference_triggers_a_recheck_of_already_clear_views(
    store: Store,
) -> None:
    _two_day_view(store)
    await check_views(store, Routed(checks=[_verdict(False)]), REL)
    assert len(card_views(store.self_beliefs(REL), store.view_state(REL))) == 1
    _say(store, 70 * 30, Speaker.USER, "please stop doing short replies, i hate them")
    new_pref: Json = {
        "beliefs": [
            {
                "ref": "m3",
                "quote": "please stop doing short replies",
                "claim": "The user wants the companion to stop giving short replies.",
                "subject": "user",
                "kind": "boundary",
                "provenance": "stated",
                "confidence": 0.9,
                "lasting": True,
                "sensitivity": 0,
            }
        ]
    }
    ex = Routed(users=[new_pref], checks=[_verdict(True, "k1")])
    result = await reflect_once(store, ex, REL)
    assert result.views_checked == 1
    assert result.views_conflicts == 1
    assert card_views(store.self_beliefs(REL), store.view_state(REL)) == ()


async def test_an_unparseable_check_leaves_the_view_unchecked_and_out(store: Store) -> None:
    _two_day_view(store)
    result = await check_views(store, Routed(checks=[{"nonsense": True}]), REL)
    assert result.checked == 0
    assert card_views(store.self_beliefs(REL), store.view_state(REL)) == ()


async def test_the_mode_setting_is_remembered_and_changes_what_is_carried(store: Store) -> None:
    _two_day_view(store)
    await check_views(store, Routed(checks=[_verdict(False)]), REL)
    assert len(card_views(store.self_beliefs(REL), store.view_state(REL))) == 1
    store.set_setting(REL, VIEWS_MODE_KEY, "review", T0)
    assert card_views(store.self_beliefs(REL), store.view_state(REL)) == ()
    store.set_setting(REL, VIEWS_MODE_KEY, "auto", T0 + timedelta(minutes=1))
    assert len(card_views(store.self_beliefs(REL), store.view_state(REL))) == 1
    store.set_setting(REL, VIEWS_MODE_KEY, "off", T0 + timedelta(minutes=2))
    assert card_views(store.self_beliefs(REL), store.view_state(REL)) == ()


async def _carried_turn(store: Store) -> TurnId:
    _two_day_view(store)
    await check_views(store, Routed(checks=[_verdict(False)]), REL)
    talker = _Talker()
    await Conversation(store, talker, PREFIX, REL).handle(
        SessionId("s"), "hi", "test", T0 + timedelta(days=3)
    )
    assert "short replies read as more human" in talker.seen[0].messages[-1].content
    turn = store.latest_turn(REL)
    assert turn is not None
    return turn


def _implication(labels: list[str], confidence: float = 0.9) -> Json:
    return {"implicated": list(labels), "confidence": confidence}  # type: ignore[dict-item]


async def test_a_flag_that_implicates_a_view_retires_only_that_view(store: Store) -> None:
    turn = await _carried_turn(store)
    ex = Routed(implications=[_implication(["v1"])])
    hit = await views_implicated(store, ex, REL, turn, "it contradicted its own view about replies")
    assert [b.id for b in hit] == ["idea"]
    assert "short replies read as more human" in ex.prompts["flag"][0]
    assert retire_implicated_views(store, hit) == [
        "The companion thinks short replies read as more human."
    ]
    assert store.self_beliefs(REL) == []
    assert len(store.self_beliefs_all(REL)) == 1  # closed, never deleted


async def test_a_flag_about_something_else_retires_nothing(store: Store) -> None:
    """The game-loop flag that closed four unrelated views."""
    turn = await _carried_turn(store)
    hit = await views_implicated(
        store, Routed(implications=[_implication([])]), REL, turn, "weird memory reset/loop?"
    )
    assert hit == []
    assert len(store.self_beliefs(REL)) == 1


async def test_a_low_confidence_judgement_retires_nothing(store: Store) -> None:
    turn = await _carried_turn(store)
    ex = Routed(implications=[_implication(["v1"], confidence=0.5)])
    assert await views_implicated(store, ex, REL, turn, "off") == []


async def test_an_unparseable_or_failed_judgement_retires_nothing(store: Store) -> None:
    turn = await _carried_turn(store)
    assert await views_implicated(store, Routed(implications=[{"x": 1}]), REL, turn, "off") == []

    class Boom:
        async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
            msg = "provider down"
            raise RuntimeError(msg)

    assert await views_implicated(store, Boom(), REL, turn, "off") == []
    assert len(store.self_beliefs(REL)) == 1


async def test_a_label_the_model_invents_is_ignored(store: Store) -> None:
    turn = await _carried_turn(store)
    ex = Routed(implications=[_implication(["v9"])])
    assert await views_implicated(store, ex, REL, turn, "off") == []


async def test_a_turn_that_carried_no_views_never_asks_the_model(store: Store) -> None:
    talker = _Talker()
    await Conversation(store, talker, PREFIX, REL).handle(SessionId("s"), "hi", "test", T0)
    turn = store.latest_turn(REL)
    assert turn is not None
    ex = Routed()
    assert await views_implicated(store, ex, REL, turn, "off") == []
    assert ex.prompts["flag"] == []


async def test_calibration_compares_the_gates_with_the_users_decisions(store: Store) -> None:
    from companion.loops.calibrate import reviewed_views  # noqa: PLC0415

    _two_day_view(store, "good")  # gates would adopt it, and the user approves it
    store.insert_belief(
        _own_view(
            "bad",
            "u1",
            "short replies read as more human",
            "The companion thinks short replies read as more human, really.",
        )
    )
    store.add_evidence(
        BeliefId("bad"), Evidence(UtteranceId(f"u{60 * 30}"), "short replies read as more human")
    )
    await check_views(
        store,
        Routed(
            checks=[
                {
                    "results": [
                        {"view": "v1", "conflicts": False, "confidence": 0.9},
                        {"view": "v2", "conflicts": False, "confidence": 0.9},
                    ]
                }
            ]
        ),
        REL,
    )
    store.approve_view(BeliefId("good"), T0)
    from companion.loops.curate import retire  # noqa: PLC0415

    retire(store, REL, "bad", "not something i want it to hold")
    rows = reviewed_views(store, REL)
    by = {str(r.belief.id): r for r in rows}
    assert by["good"].verdict == "approved"
    assert by["good"].gates.eligible
    assert by["bad"].verdict == "retired"
    assert by["bad"].gates.eligible  # the gates would have let it through, and the user rejected it
    from companion.loops.calibrate import report  # noqa: PLC0415

    text = report(rows)
    assert "1 of 2 adopted views were ones you wanted (50%)" in text
    assert "would have adopted, but you retired" in text


async def test_a_user_reason_containing_the_word_duplicate_still_counts_as_a_decision(
    store: Store,
) -> None:
    from companion.loops.calibrate import reviewed_views  # noqa: PLC0415
    from companion.loops.curate import retire  # noqa: PLC0415

    _two_day_view(store, "v")
    retire(store, REL, "v", "near-duplicate of an approved view")
    assert [r.verdict for r in reviewed_views(store, REL)] == ["retired"]


async def test_a_mechanical_dedupe_closure_is_not_a_user_decision(store: Store) -> None:
    from companion.loops.calibrate import reviewed_views  # noqa: PLC0415
    from companion.loops.curate import close_duplicates  # noqa: PLC0415

    _two_day_view(store, "keep")
    store.insert_belief(
        _own_view("dupe", "u1", "short replies read as more human", "short replies read as human.")
    )
    close_duplicates(store, REL)
    assert reviewed_views(store, REL) == []


async def test_a_retired_view_is_not_recorded_again_when_the_ledger_is_re_read(
    store: Store,
) -> None:
    from companion.loops.curate import retire  # noqa: PLC0415
    from companion.loops.slow import reflect_from  # noqa: PLC0415

    _say(store, 1, Speaker.COMPANION, VIEW_TEXT)
    await reflect_once(store, Routed(views=[_view("m1", "lazy is a flaw")]), REL)
    [v] = store.self_beliefs(REL)
    retire(store, REL, v.id[:8], "not a view i want it to hold")
    assert [b.id for b in store.rejected_views(REL)] == [v.id]

    spy = Routed(views=[_view("m1", "lazy is a flaw")])
    result = await reflect_from(store, spy, REL, None)
    assert result.views_accepted == 0
    assert store.self_beliefs(REL) == []
    assert "Rejected by the user" in spy.prompts["self"][0]
    assert "laziness is not a flaw" in spy.prompts["self"][0]


async def test_a_mechanical_dedupe_closure_is_not_a_rejection(store: Store) -> None:
    from companion.loops.curate import close_duplicates  # noqa: PLC0415

    _two_day_view(store, "keep")
    store.insert_belief(
        _own_view("dupe", "u1", "short replies read as more human", "short replies read as human.")
    )
    close_duplicates(store, REL)
    assert store.rejected_views(REL) == []


async def test_a_view_closed_because_a_flag_implicated_it_counts_as_rejected(
    store: Store,
) -> None:
    turn = await _carried_turn(store)
    hit = await views_implicated(store, Routed(implications=[_implication(["v1"])]), REL, turn, "x")
    retire_implicated_views(store, hit)
    assert [b.id for b in store.rejected_views(REL)] == ["idea"]
