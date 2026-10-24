from __future__ import annotations

from pathlib import Path

from companion.core.card import Card
from companion.core.extractor import Extraction
from companion.core.turn.listening import Judgement
from companion.core.types import Frame, Json, TurnId
from companion.features.nudges.run import away_in_turn
from companion.loops.conversation import Conversation
from companion.loops.current import Heard, Turn
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
