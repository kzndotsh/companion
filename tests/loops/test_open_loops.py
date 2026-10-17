from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.initiative import Caps
from companion.core.openloops import LoopState, OpenLoop
from companion.core.types import (
    DecisionKind,
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.loops.openloops import Ticker, extract_open_loops, short_draft, tick
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SAID = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)  # a Monday
LATER = datetime(2026, 10, 14, 13, 0, tzinfo=UTC)  # Wednesday, past the follow-up time


class Fake:
    def __init__(self, data: Json) -> None:
        self.data = data

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        return Extraction(data=self.data, model="fake", cost_usd=0.001, latency_ms=3)


class Boom:
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        msg = "down"
        raise RuntimeError(msg)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _said(store: Store, text: str = "going to the vet tomorrow, wish me luck") -> Utterance:
    u = Utterance(
        UtteranceId("u1"),
        REL,
        SessionId("s"),
        TurnId("t1"),
        Speaker.USER,
        text,
        Frame.REAL,
        "test",
        SAID,
    )
    store.append_utterance(u)
    return u


def _item(**over: object) -> dict[str, Json]:
    item: dict[str, Json] = {
        "ref": "m1",
        "quote": "going to the vet tomorrow",
        "claim": "vet visit",
        "when": "tomorrow",
        "scale": "days",
        "sensitivity": 0,
    }
    item.update(over)  # type: ignore[arg-type]
    return item


async def _extract(store: Store, u: Utterance, data: Json) -> tuple[int, int, list[str]]:
    notes: list[str] = []
    counts = await extract_open_loops(
        store,
        Fake(data),
        REL,
        {"m1": u},
        {u.id},
        (SAID + timedelta(minutes=1), UTC),
        lambda reason, detail: notes.append(reason),
    )
    return counts.stored, counts.rejected, notes


async def test_a_loop_is_recorded_with_its_quote_and_a_follow_up_time(store: Store) -> None:
    u = _said(store)
    stored, rejected, notes = await _extract(store, u, {"loops": [_item()]})
    assert (stored, rejected) == (1, 0)
    loop = store.open_loops(REL)[0]
    assert loop.claim == "vet visit"
    assert loop.quote == "going to the vet tomorrow"
    assert loop.follow_up_at == datetime(2026, 10, 14, 10, 0, tzinfo=UTC)
    assert any("recorded from their own words" in n for n in notes)


async def test_sensitive_minute_scale_and_repeated_loops_are_not_recorded(store: Store) -> None:
    u = _said(store)
    data: Json = {
        "loops": [_item(sensitivity=2), _item(scale="minutes", claim="snack"), _item(), _item()]
    }
    stored, rejected, notes = await _extract(store, u, data)
    assert stored == 1
    assert rejected == 3
    assert any("sensitive" in n for n in notes)
    assert any("minute-scale" in n for n in notes)
    assert any("already recorded" in n for n in notes)


async def test_a_malformed_answer_or_a_failing_model_records_nothing_and_does_not_raise(
    store: Store,
) -> None:
    u = _said(store)
    assert (await _extract(store, u, {"unexpected": 1}))[0] == 0
    counts = await extract_open_loops(
        store, Boom(), REL, {"m1": u}, {u.id}, (SAID, UTC), lambda reason, detail: None
    )
    assert counts.stored == 0
    assert store.open_loops(REL) == []


async def _recorded(store: Store) -> OpenLoop:
    await _extract(store, _said(store), {"loops": [_item()]})
    return store.open_loops(REL)[0]


async def _draft(loop: OpenLoop) -> str:
    return f"how did the {loop.claim} go?"


def test_a_long_draft_is_cut_to_its_first_sentence_or_dropped() -> None:
    assert short_draft("how did the vet go?") == "how did the vet go?"
    long_two = "how did the vet go? " + "and also " * 12
    assert short_draft(long_two) == "how did the vet go?"
    assert short_draft("you said you were annoyed. " + "and also " * 12) == ""
    assert short_draft("word " * 30) == ""


async def test_a_shadow_tick_records_the_draft_and_marks_the_loop_asked_without_sending(
    store: Store,
) -> None:
    loop = await _recorded(store)
    verdict = await tick(store, REL, LATER, UTC, _draft, Ticker())
    assert verdict.send
    reach = store.reach_outs(REL)
    assert len(reach) == 1
    assert reach[0].mode == "shadow"
    assert reach[0].draft == "how did the vet visit go?"
    assert reach[0].loop_id == loop.id
    assert store.open_loops(REL)[0].state is LoopState.ASKED
    initiated = store.decisions_of_kind(REL, DecisionKind.INITIATE)
    assert len(initiated) == 1
    assert initiated[0].reason.startswith("shadow, would send: due ")


async def test_an_asked_loop_is_not_asked_again_and_the_daily_cap_holds(store: Store) -> None:
    await _recorded(store)
    ticker = Ticker()
    assert (await tick(store, REL, LATER, UTC, _draft, ticker)).send
    again = await tick(store, REL, LATER + timedelta(hours=1), UTC, _draft, ticker)
    assert not again.send
    assert len(store.reach_outs(REL)) == 1


async def test_a_hold_is_recorded_once_with_its_reason_not_every_tick(store: Store) -> None:
    await _recorded(store)
    ticker = Ticker()
    night = LATER.replace(hour=23, minute=30)
    for minutes in (0, 15, 30):
        v = await tick(store, REL, night + timedelta(minutes=minutes), UTC, _draft, ticker)
        assert not v.send
    held = store.decisions_of_kind(REL, DecisionKind.DO_NOTHING)
    assert len(held) == 1
    assert "quiet hours" in held[0].reason
    assert store.reach_outs(REL) == []
    assert store.open_loops(REL)[0].state is LoopState.OPEN  # held, so still waiting


async def test_a_loop_past_its_horizon_expires_and_is_never_sent(store: Store) -> None:
    await _recorded(store)
    far = LATER + timedelta(days=10)
    verdict = await tick(store, REL, far, UTC, _draft, Ticker(), Caps())
    assert not verdict.send
    assert store.open_loops(REL)[0].state is LoopState.EXPIRED
    assert store.reach_outs(REL) == []
