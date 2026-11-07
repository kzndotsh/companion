from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.reachout import Dial, Fate, Kind
from companion.core.types import (
    Frame,
    Json,
    RelationshipId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.reach.gate import Hold
from companion.features.reach.logic import PACED
from companion.features.reach.outcome import OUTCOME, STOPPED
from companion.features.reach.run import (
    Reacher,
    holds,
    record_outcomes,
    resume,
    situation,
    tick_reach,
)
from companion.features.reach.store import Own, Reaches
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
SENT_AT = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
H = timedelta(hours=1)


class Reader:
    """Answers every read of how they took it with `landed`, and counts the reads."""

    def __init__(self, landed: str) -> None:
        self.landed = landed
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction({"landed": self.landed}, "fake", 0.0001, 3)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _reach_out(store: Store, fate: Fate, rid: str = "r1", at: datetime = SENT_AT) -> None:
    store.part(Reaches).add(Own(rid, REL, Kind.THOUGHT, "", "saw a cat", fate, {}, at))


def _said(store: Store, at: datetime, text: str, uid: str = "u1") -> None:
    store.append_utterance(
        Utterance(UtteranceId(uid), REL, TurnId(uid), Speaker.USER, text, Frame.REAL, "test", at)
    )


def _outcomes(store: Store) -> list[dict[str, Json]]:
    return [d.detail or {} for d in store.decisions_with_key(REL, OUTCOME)]


async def test_a_shadow_reach_out_is_recorded_once_as_the_base_rate_without_a_read(
    store: Store,
) -> None:
    _reach_out(store, Fate.SHADOW)
    _said(store, SENT_AT + 9 * H, "morning, what did i miss")
    reader = Reader("picked_up")
    assert await record_outcomes(store, REL, SENT_AT + 10 * H, reader) == 1
    assert await record_outcomes(store, REL, SENT_AT + 11 * H, reader) == 0
    [got] = _outcomes(store)
    assert (got["base_rate"], got["answered"], got["after_hours"], got["landed"]) == (
        True,
        True,
        9.0,
        None,
    )
    assert reader.calls == 0


async def test_a_dropped_draft_has_no_outcome(store: Store) -> None:
    _reach_out(store, Fate.DROPPED)
    assert await record_outcomes(store, REL, SENT_AT + 49 * H, Reader("ignored")) == 0


async def test_a_live_answer_is_read_for_how_they_took_it(store: Store) -> None:
    _reach_out(store, Fate.LIVE)
    _said(store, SENT_AT + H, "omg yes, send a pic")
    reader = Reader("picked_up")
    await record_outcomes(store, REL, SENT_AT + 2 * H, reader)
    [got] = _outcomes(store)
    assert (got["mode"], got["landed"]) == ("live", "picked_up")
    assert reader.calls == 1


async def test_a_stop_holds_every_reach_out_until_resumed(store: Store) -> None:
    _reach_out(store, Fate.LIVE)
    _said(store, SENT_AT + H, "please don't text me first like that")
    now = SENT_AT + 20 * H
    await record_outcomes(store, REL, SENT_AT + 2 * H, Reader("asked_to_stop"))
    assert store.decisions_with_key(REL, STOPPED)
    held = holds(store, REL, (now, UTC), Reacher(Dial.WARM, None))
    assert held is not None
    assert held.what == Hold.STOPPED.value
    assert resume(store, REL, now)
    assert not resume(store, REL, now)
    after = holds(store, REL, (now + H, UTC), Reacher(Dial.WARM, None))
    assert after is None or after.what != Hold.STOPPED.value


async def test_a_late_answer_to_a_shadow_one_never_steps_the_dial_down(store: Store) -> None:
    _reach_out(store, Fate.SHADOW)
    _said(store, SENT_AT + 30 * H, "hey")
    sit, _ = situation(store, REL, (SENT_AT + 40 * H, UTC), Reacher(Dial.WARM, None))
    assert sit.paced is None
    await tick_reach(store, REL, (SENT_AT + 40 * H, UTC), Reacher(Dial.WARM, None))
    assert not store.decisions_with_key(REL, PACED)


async def test_a_late_answer_to_a_live_one_steps_it_down(store: Store) -> None:
    _reach_out(store, Fate.LIVE)
    _said(store, SENT_AT + 30 * H, "hey")
    sit, _ = situation(store, REL, (SENT_AT + 40 * H, UTC), Reacher(Dial.WARM, None))
    assert sit.paced is not None
