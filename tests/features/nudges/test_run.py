from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from companion.core.extractor import Extraction
from companion.core.reachout import WOULD_NUDGE, Held
from companion.core.turn.listening import Judgement
from companion.core.turn.now import KEY as NOW_KEY
from companion.core.types import Json, TraceId, TurnId
from companion.features.nudges.run import NUDGE_DROPPED, tick_nudge
from companion.loops.current import Heard
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store
from tests.turn.test_mood_loop import NOW, REL, SESSION

CALM: Heard = (Judgement(severity=0, stance="other", vague=False, age_coded=False), "j", "p")


class Drafts:
    def __init__(self, message: str) -> None:
        self.message, self.calls = message, 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction({"message": self.message}, "j", 0.0, 1)


def _stepped_away(tmp_path: Path) -> Store:
    store = Store(tmp_path / "away.sqlite")
    detail: dict[str, Json] = {
        "phase": "leaving",
        "what": "they will shower",
        "minutes": 20,
        "said": "brb, shower",
    }
    Recorder(store, REL, SESSION, TurnId("t1"), TraceId("t1"), NOW).decide(NOW_KEY, detail)
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
