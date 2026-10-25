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
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.reach.logic import Dial
from companion.features.reach.run import Reacher, holds
from companion.features.threads.gate import Verdict
from companion.features.threads.logic import Thread, ThreadState
from companion.features.threads.run import (
    Draft,
    Reading,
    Ticker,
    catch_up_loops,
    draft_text,
    extract_open_loops,
    tick,
)
from companion.features.threads.store import ReachOut
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


async def _tick(
    store: Store, now: datetime, draft: Draft | None = None, ticker: Ticker | None = None
) -> Verdict:
    """One plan tick behind the shared gate, as the daemon runs it (ADR 0023)."""
    held = holds(store, REL, (now, UTC), Reacher(Dial.WARM, None))
    return await tick(store, REL, now, UTC, draft or _draft, ticker or Ticker(), held=held)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _said(
    store: Store,
    text: str = "going to the vet tomorrow, wish me luck",
    uid: str = "u1",
    at: datetime = SAID,
) -> Utterance:
    u = Utterance(
        UtteranceId(uid),
        REL,
        SessionId("s"),
        TurnId("t1"),
        Speaker.USER,
        text,
        Frame.REAL,
        "test",
        at,
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
        "certainty": "firm",
        "about_companion": False,
        "kind": "follow_up",
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
    assert counts is not None
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
    assert counts is None  # a failed call says so, so the batch can be read again
    assert store.open_loops(REL) == []


async def _recorded(store: Store) -> Thread:
    await _extract(store, _said(store), {"loops": [_item()]})
    return store.open_loops(REL)[0]


async def _draft(loop: Thread) -> str:
    return f"how did the {loop.claim} go?"


def test_a_long_draft_is_kept_whole_and_only_an_empty_one_is_dropped() -> None:
    long_two = "how did the vet go? " + "and also " * 12
    assert draft_text(long_two) == long_two.strip()  # never cut to its first sentence
    assert draft_text("  how   did the vet go?\n") == "how did the vet go?"
    assert draft_text("   ") == ""


async def test_a_shadow_tick_records_the_draft_and_marks_the_loop_asked_without_sending(
    store: Store,
) -> None:
    loop = await _recorded(store)
    verdict = await _tick(store, LATER)
    assert verdict.send
    reach = store.reach_outs(REL)
    assert len(reach) == 1
    assert reach[0].mode == "shadow"
    assert reach[0].draft == "how did the vet visit go?"
    assert reach[0].loop_id == loop.id
    assert store.open_loops(REL)[0].state is ThreadState.ASKED
    initiated = store.decisions_of_kind(REL, DecisionKind.INITIATE)
    assert len(initiated) == 1
    assert initiated[0].reason.startswith("shadow, would send: due ")


async def test_an_asked_loop_is_not_asked_again_and_the_daily_cap_holds(store: Store) -> None:
    await _recorded(store)
    ticker = Ticker()
    assert (await _tick(store, LATER, ticker=ticker)).send
    again = await _tick(store, LATER + timedelta(hours=1), ticker=ticker)
    assert not again.send
    assert len(store.reach_outs(REL)) == 1


async def test_a_hold_is_recorded_once_with_its_reason_not_every_tick(store: Store) -> None:
    await _recorded(store)
    ticker = Ticker()
    night = LATER.replace(hour=23, minute=30)
    for minutes in (0, 15, 30):
        v = await _tick(store, night + timedelta(minutes=minutes), ticker=ticker)
        assert not v.send
    held = store.decisions_of_kind(REL, DecisionKind.DO_NOTHING)
    assert len(held) == 1
    assert "quiet hours" in held[0].reason
    assert store.reach_outs(REL) == []
    assert store.open_loops(REL)[0].state is ThreadState.OPEN  # held, so still waiting


async def test_a_loop_past_its_horizon_expires_and_is_never_sent(store: Store) -> None:
    await _recorded(store)
    far = LATER + timedelta(days=10)
    verdict = await _tick(store, far)
    assert not verdict.send
    assert store.open_loops(REL)[0].state is ThreadState.EXPIRED
    assert store.reach_outs(REL) == []


class Seen(Fake):
    def __init__(self, data: Json) -> None:
        super().__init__(data)
        self.prompts: list[str] = []

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        self.prompts.append(user)
        return await super().extract(system, user, schema)


async def test_a_loop_they_settle_themselves_is_closed_and_never_asked_about(store: Store) -> None:
    loop = await _recorded(store)
    u = _said(store, "the vet went fine, she is all good", "u2", SAID + timedelta(hours=1))
    data: Json = {
        "loops": [],
        "resolved": [{"loop": "L1", "ref": "m2", "quote": "the vet went fine"}],
    }
    model = Seen(data)
    notes: list[str] = []
    counts = await extract_open_loops(
        store, model, REL, {"m2": u}, {u.id}, (SAID, UTC), lambda r, d: notes.append(r)
    )
    assert counts is not None
    assert counts.resolved == 1
    assert "[L1] vet visit" in model.prompts[0]
    assert store.open_loops(REL)[0].state is ThreadState.RESOLVED
    assert any("they brought it up themselves" in n for n in notes)
    verdict = await _tick(store, LATER)
    assert not verdict.send
    assert store.reach_outs(REL) == []
    del loop


async def test_a_reach_out_they_never_answered_holds_the_next_one(store: Store) -> None:
    """The shared gate counts every reach-out, a shadow would-send as sent, so shadow shows what
    live would do (ADR 0021, 0023)."""
    loop = await _recorded(store)
    for mode in ("live", "shadow"):
        at = LATER - timedelta(hours=30)
        store.add_reach_out(ReachOut(f"r-{mode}", REL, loop.id, mode, "how?", "due", at))
        verdict = await _tick(store, LATER)
        assert not verdict.send
        assert "not written since its last reach-out" in verdict.reason


async def test_no_paid_draft_is_made_unless_every_cheap_gate_passes(store: Store) -> None:
    calls: list[str] = []

    async def counting(loop: Thread) -> str:
        calls.append(loop.id)
        return "how did it go?"

    await _recorded(store)
    not_due = SAID + timedelta(hours=1)
    night = datetime(2026, 10, 15, 3, 0, tzinfo=UTC)  # due, but in quiet hours
    for now in (not_due, night):
        assert not (await _tick(store, now, counting)).send
    _said(store, "back again", "u9", LATER - timedelta(minutes=10))
    assert not (await _tick(store, LATER, counting)).send
    assert calls == []
    assert (await _tick(store, LATER + timedelta(hours=2), counting)).send
    assert len(calls) == 1


class Flaky:
    """Fails the first `fails` calls, then answers with one loop."""

    def __init__(self, fails: int) -> None:
        self.fails, self.calls = fails, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        if self.calls <= self.fails:
            msg = "down"
            raise RuntimeError(msg)
        return Extraction(data={"loops": [_item()]}, model="fake", cost_usd=0.0, latency_ms=1)


async def _catch_up(store: Store, model: Flaky) -> list[str]:
    notes: list[str] = []
    await catch_up_loops(
        store, model, REL, (LATER, UTC), lambda r, d: notes.append(r), Reading(40, 4, batches=1)
    )
    return notes


async def test_a_failed_loop_pass_keeps_its_place_and_the_plan_is_read_next_time(
    store: Store,
) -> None:
    _said(store)
    model = Flaky(fails=1)
    await _catch_up(store, model)
    assert store.open_loops(REL) == []
    assert store.loop_cursor(REL) is None  # the bookmark did not move past the failed batch
    await _catch_up(store, model)
    assert [lp.claim for lp in store.open_loops(REL)] == ["vet visit"]
    assert store.loop_cursor(REL) is not None


async def test_a_batch_that_keeps_failing_is_let_go_after_three_tries(store: Store) -> None:
    _said(store)
    model = Flaky(fails=99)
    notes = [n for _ in range(3) for n in await _catch_up(store, model)]
    assert store.loop_cursor(REL) is not None  # let go, so plans never block on one batch
    assert any("gave up on a batch after 3 failed tries" in n for n in notes)
    calls = model.calls
    await _catch_up(store, model)
    assert model.calls == calls  # nothing left to read
