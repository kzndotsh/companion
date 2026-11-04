from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.reach.logic import DROPPED, HELD, WOULD_SEND, Dial, Kind
from companion.features.reach.run import Reacher, tick_reach
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
NOW = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)  # 3 PM, a usual hour on the baseline
WHEN = (NOW, UTC)


class Drafter:
    """Brainstorms one idea, `message`, and picks idea `pick` (0 for none). `calls` counts
    brainstorms, the first paid call."""

    def __init__(self, message: str, pick: int = 1) -> None:
        self.message = message
        self.pick = pick
        self.calls = 0
        self.seen: list[str] = []

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system
        props = schema.get("properties")
        if isinstance(props, dict) and "pick" in props:
            return Extraction({"pick": self.pick, "why": "fits"}, "fake", 0.0001, 3)
        self.calls += 1
        self.seen.append(user)
        idea: Json = {"angle": "ask", "message": self.message, "about": "a thread"}
        return Extraction({"ideas": [idea]}, "fake", 0.0001, 3)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _said(store: Store, at: datetime, uid: str = "u1", speaker: Speaker = Speaker.USER) -> None:
    store.append_utterance(
        Utterance(
            UtteranceId(uid),
            REL,
            SessionId("s"),
            TurnId(uid),
            speaker,
            "off to bed, night!",
            Frame.REAL,
            "test",
            at,
        )
    )


def _companion_messages(store: Store) -> int:
    return sum(
        1
        for u in store.history_before(REL, NOW + timedelta(days=1), 100)
        if u.speaker is Speaker.COMPANION
    )


def _keys(store: Store, kind: DecisionKind, key: str) -> int:
    return sum(1 for d in store.decisions_with_key(REL, key) if d.kind is kind)


async def test_a_shadow_tick_records_a_would_send_and_sends_nothing(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))  # past the 12-hour baseline pause
    drafter = Drafter("missed you a little today 🙂 how's the bread coming along?")
    reacher = Reacher(Dial.WARM, drafter)
    row = await tick_reach(store, REL, WHEN, reacher)
    assert row is not None
    assert (row.kind, row.mode, row.draft) == (Kind.MISSING, "shadow", drafter.message)
    assert row.detail["dial"] == "warm"
    assert isinstance(row.detail["rhythm"], dict)
    assert _keys(store, DecisionKind.INITIATE, WOULD_SEND) == 1
    assert _companion_messages(store) == 0  # nothing was sent or stored as said
    # The next tick: they have not written since, so it waits for them, without a paid call.
    again = await tick_reach(store, REL, (NOW + timedelta(hours=6), UTC), reacher)
    assert again is None
    assert drafter.calls == 1
    held = store.decisions_with_key(REL, HELD)
    assert [(d.detail or {}).get("hold") for d in held] == ["the last one is unanswered"]


async def test_no_paid_call_is_made_unless_every_check_passes(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("thinking of you")
    night = NOW.replace(hour=1)
    _said(store, night - timedelta(hours=14), "u0")
    assert await tick_reach(store, REL, (night, UTC), Reacher(Dial.WARM, drafter)) is None
    assert await tick_reach(store, REL, WHEN, Reacher(Dial.OFF, drafter)) is None
    assert drafter.calls == 0
    assert store.own_reach_outs(REL) == []


async def test_a_plan_or_a_nudge_this_tick_goes_first(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("hey you")
    assert await tick_reach(store, REL, WHEN, Reacher(Dial.WARM, drafter), Kind.PLAN) is None
    assert drafter.calls == 0


async def test_a_needy_draft_is_dropped_and_recorded(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("you've been quiet all day, everything okay?")
    reacher = Reacher(Dial.WARM, drafter)
    assert await tick_reach(store, REL, WHEN, reacher) is None
    rows = store.own_reach_outs(REL)
    assert [(r.mode, r.draft) for r in rows] == [("dropped", "")]
    why = "how long they have been gone"
    assert rows[0].detail["screened_out"] == [{"message": drafter.message, "why": why}]
    assert _keys(store, DecisionKind.DO_NOTHING, DROPPED) == 1
    assert _keys(store, DecisionKind.INITIATE, WOULD_SEND) == 0
    # A dropped draft is not tried again within six hours.
    assert await tick_reach(store, REL, (NOW + timedelta(hours=1), UTC), reacher) is None
    assert drafter.calls == 1


async def test_the_initiative_command_shows_the_rhythm_the_share_and_the_would_sends(
    tmp_path: Path,
) -> None:
    from companion.cli import initiative  # noqa: PLC0415

    store = Store(tmp_path / "rel.sqlite")
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("how's the bread coming along?")
    await tick_reach(store, REL, WHEN, Reacher(Dial.NORMAL, drafter))
    await tick_reach(store, REL, (NOW + timedelta(hours=6), UTC), Reacher(Dial.NORMAL, drafter))
    store.close()
    out = initiative.run(tmp_path / "rel.sqlite", "rel", NOW + timedelta(hours=7))
    assert "COMPANION_REACH normal" in out
    assert "1 conversations in two weeks, 5% theirs and 95% baseline" in out
    assert "share it started: 1 of 2" in out
    assert "missing them" in out and drafter.message in out
    assert "1  the last one is unanswered" in out


async def test_nothing_goes_when_the_judge_picks_none_and_it_waits_six_hours(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("how's the bread coming along?", pick=0)
    reacher = Reacher(Dial.WARM, drafter)
    assert await tick_reach(store, REL, WHEN, reacher) is None
    rows = store.own_reach_outs(REL)
    assert [(r.mode, r.detail["dropped"]) for r in rows] == [
        ("dropped", "the judge sent none: fits")
    ]
    assert await tick_reach(store, REL, (NOW + timedelta(hours=1), UTC), reacher) is None
    assert drafter.calls == 1


async def test_a_text_about_the_two_of_them_is_dropped(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("no label needed on whatever this is, i just like it")
    assert await tick_reach(store, REL, WHEN, Reacher(Dial.WARM, drafter)) is None
    (row,) = store.own_reach_outs(REL)
    assert row.detail["screened_out"] == [
        {"message": drafter.message, "why": "about the relationship itself"}
    ]


async def test_it_holds_for_twelve_hours_after_a_heavy_message(store: Store) -> None:
    from companion.kit.record import Recorder  # noqa: PLC0415

    _said(store, NOW - timedelta(hours=13))
    heavy = NOW - timedelta(hours=11)
    Recorder(store, REL, SessionId("s"), TurnId("t"), TraceId("t"), heavy).decide(
        "listening", {"labels": {"severity": 2}}, reason="listening: severity 2"
    )
    drafter = Drafter("how's the bread coming along?")
    assert await tick_reach(store, REL, WHEN, Reacher(Dial.WARM, drafter)) is None
    assert drafter.calls == 0
    (held,) = store.decisions_with_key(REL, HELD)
    assert (held.detail or {}).get("hold") == "a heavy chat lately"


async def test_the_brainstorm_sees_their_last_lines_and_never_a_scene(store: Store) -> None:
    _said(store, NOW - timedelta(hours=13))
    drafter = Drafter("how's the bread coming along?")
    await tick_reach(store, REL, WHEN, Reacher(Dial.WARM, drafter))
    (seen,) = drafter.seen
    assert "them: off to bed, night!" in seen
    assert "Why now: missing them" in seen
    assert "Tuesday 20 October" in seen


async def test_an_intimate_last_chat_is_kept_out_of_the_brainstorm(store: Store) -> None:
    from companion.kit.record import Recorder  # noqa: PLC0415

    said = NOW - timedelta(hours=13)
    _said(store, said)
    Recorder(store, REL, SessionId("s"), TurnId("t"), TraceId("t"), said).decide(
        "listening", {"labels": {"severity": 0, "intimate": True}}, reason="listening: severity 0"
    )
    drafter = Drafter("how's the bread coming along?")
    await tick_reach(store, REL, WHEN, Reacher(Dial.WARM, drafter))
    (seen,) = drafter.seen
    assert "off to bed" not in seen


async def test_a_heavy_last_chat_is_kept_out_of_the_brainstorm_past_the_hold(store: Store) -> None:
    from companion.kit.record import Recorder  # noqa: PLC0415

    said = NOW - timedelta(hours=13)  # past the 12-hour hold, so it reaches out, without the lines
    _said(store, said)
    Recorder(store, REL, SessionId("s"), TurnId("t"), TraceId("t"), said).decide(
        "listening", {"labels": {"severity": 3, "intimate": False}}, reason="listening: severity 3"
    )
    drafter = Drafter("how's the bread coming along?")
    await tick_reach(store, REL, WHEN, Reacher(Dial.WARM, drafter))
    (seen,) = drafter.seen
    assert "off to bed" not in seen
