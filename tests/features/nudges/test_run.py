from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from companion.core.card import Card
from companion.core.extractor import Extraction
from companion.core.reachout import WOULD_NUDGE, Held
from companion.core.turn.listening import Judgement
from companion.core.types import Frame, Json, TraceId, TurnId
from companion.features.nudges.logic import AWAY
from companion.features.nudges.run import NUDGE_DROPPED, away_in_turn, tick_nudge
from companion.loops.conversation import Conversation
from companion.loops.current import Heard, Turn
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Talker

CALM: Heard = (Judgement(severity=0, stance="other", vague=False, age_coded=False), "j", "p")


class Away:
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction({"away": "brief", "minutes": 20}, "j", 0.0, 1)


async def _read(tmp_path: Path, *, initiative: bool) -> int:
    judge = Away()
    c = Conversation(
        Store(tmp_path / f"{initiative}.sqlite"),
        Talker(),
        PREFIX,
        REL,
        judge=judge,
        initiative=initiative,
    )
    await away_in_turn(
        c,
        Turn(SESSION, TurnId("t"), NOW, [], "brb, shower"),
        Frame.REAL,
        CALM,
        Card((), (), (), (), {}, NOW),
    )
    return judge.calls


async def test_the_away_read_runs_only_while_reaching_out_is_on(tmp_path: Path) -> None:
    assert await _read(tmp_path, initiative=True) == 1
    assert await _read(tmp_path, initiative=False) == 0


class Drafts:
    def __init__(self, message: str) -> None:
        self.message, self.calls = message, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction({"message": self.message}, "j", 0.0, 1)


def _stepped_away(tmp_path: Path) -> Store:
    store = Store(tmp_path / "away.sqlite")
    detail: dict[str, Json] = {"kind": "brief", "minutes": 20, "said": "brb, shower"}
    Recorder(store, REL, SESSION, TurnId("t1"), TraceId("t1"), NOW).decide(AWAY, detail)
    return store


async def test_a_light_draft_is_recorded_as_a_would_send(tmp_path: Path) -> None:
    store = _stepped_away(tmp_path)
    got = await tick_nudge(store, REL, NOW + timedelta(hours=2), Drafts("how was it?"), held=None)
    assert got == "how was it?"
    assert len(store.decisions_with_key(REL, WOULD_NUDGE)) == 1


async def test_a_needy_draft_is_dropped_never_counted_and_not_tried_again(tmp_path: Path) -> None:
    store = _stepped_away(tmp_path)
    drafts = Drafts("where have you been??")
    later = NOW + timedelta(hours=2)
    assert await tick_nudge(store, REL, later, drafts, held=None) is None
    assert await tick_nudge(store, REL, later + timedelta(minutes=15), drafts, held=None) is None
    assert drafts.calls == 1
    assert store.decisions_with_key(REL, WOULD_NUDGE) == []
    assert len(store.decisions_with_key(REL, NUDGE_DROPPED)) == 1


async def test_a_hold_from_the_shared_gate_spends_nothing(tmp_path: Path) -> None:
    store = _stepped_away(tmp_path)
    drafts = Drafts("how was it?")
    held = Held("quiet hours", "3:00 is one of their quiet hours")
    assert await tick_nudge(store, REL, NOW + timedelta(hours=2), drafts, held=held) is None
    assert drafts.calls == 0
