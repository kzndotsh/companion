from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.turn.address import KEY as ADDRESS_KEY
from companion.core.types import Frame, Json, Speaker, TurnId, Utterance, UtteranceId
from companion.features.curiosity.basics.logic import name_belief
from companion.features.threads.logic import Thread, ThreadState
from companion.kit.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn.beside import settled
from companion.turn.fast import handle
from companion.turn.mention import MET, PACE_SOONER
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "rel.sqlite")
    said = Utterance(
        UtteranceId("u0"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "sam, and the vet is tomorrow",
        Frame.REAL,
        "test",
        NOW - timedelta(days=1),
    )
    s.append_utterance(said)
    s.insert_belief(name_belief(said, "Sam", "b1", said.at))
    s.set_setting(REL, ADDRESS_KEY, "they/them", said.at)  # the basics known: no ask this turn
    s.add_open_loop(
        Thread(
            "vet",
            REL,
            "the vet visit",
            "the vet is tomorrow",
            said.id,
            NOW - timedelta(hours=1),
            0,
            said.at,
        )
    )
    return s


async def _say(store: Store, judge: Judge, at: datetime, text: str = "hey hey") -> str:
    talker = Talker()
    await handle(Runtime(store, talker, PREFIX, REL, judge=judge), SESSION, text, "test", at)
    await settled()
    return talker.seen[0].card


async def test_a_due_loop_is_offered_once_a_day_at_most_twice(store: Store) -> None:
    assert "the vet visit" in await _say(store, Judge(), NOW)
    assert store.open_loops(REL)[0].state is ThreadState.ASKED
    assert "the vet visit" not in await _say(store, Judge(), NOW + timedelta(hours=2))
    assert "the vet visit" in await _say(store, Judge(), NOW + timedelta(days=1, minutes=1))
    assert "the vet visit" not in await _say(store, Judge(), NOW + timedelta(days=2, minutes=2))


async def test_a_serious_turn_gets_no_loop_note(store: Store) -> None:
    assert "the vet visit" not in await _say(store, Judge(severity=2), NOW, "i had a rough day")
    assert store.open_loops(REL)[0].state is ThreadState.OPEN


class Meets(Judge):
    """Reads every thread as picked up; the listening judge as the plain one."""

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        props = schema["properties"]
        if isinstance(props, dict) and set(props) == {"met"}:
            return Extraction(data={"met": "picked_up"}, model="j", cost_usd=0.0, latency_ms=1)
        return await super().extract(system, user, schema)


def _met(store: Store) -> list[str | None]:
    found = store.decisions_with_key(REL, MET, NOW - timedelta(days=1))
    return [str((d.detail or {}).get("met")) for d in found]


async def test_how_they_met_a_thread_is_read_once_from_their_next_message(store: Store) -> None:
    await _say(store, Meets(), NOW)
    assert _met(store) == []  # the turn that brought it up reads nothing
    await _say(store, Meets(), NOW + timedelta(minutes=1), "it went great, she is fine")
    assert _met(store) == ["picked_up"]
    await _say(store, Meets(), NOW + timedelta(minutes=2), "anyway")
    assert _met(store) == ["picked_up"]


class SlowMeets(Meets):
    """Reads how they met it only after a long pause."""

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        props = schema["properties"]
        if isinstance(props, dict) and set(props) == {"met"}:
            await asyncio.sleep(0.2)
        return await super().extract(system, user, schema)


async def test_the_reply_does_not_wait_for_how_they_met_it(store: Store) -> None:
    await _say(store, Meets(), NOW)
    runtime = Runtime(store, Talker(), PREFIX, REL, judge=SlowMeets())
    later = NOW + timedelta(minutes=1)
    await asyncio.wait_for(handle(runtime, SESSION, "it went great", "test", later), timeout=0.15)
    assert _met(store) == []
    await settled()
    assert _met(store) == ["picked_up"]


async def test_the_learned_pace_is_logged_in_shadow_and_the_cap_still_decides(store: Store) -> None:
    await _say(store, Meets(), NOW)
    await _say(store, Meets(), NOW + timedelta(minutes=1), "it went great")
    later = NOW + timedelta(hours=17)  # picked up once: a 16h pace, under the day's cap
    assert "the vet visit" not in await _say(store, Meets(), later)
    sooner = store.decisions_with_key(REL, PACE_SOONER, NOW)
    assert len(sooner) == 1
    assert (sooner[0].detail or {})["wait_hours"] == 16
    await _say(store, Meets(), later + timedelta(minutes=5))
    assert len(store.decisions_with_key(REL, PACE_SOONER, NOW)) == 1
