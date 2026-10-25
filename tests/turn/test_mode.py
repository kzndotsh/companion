from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from companion.loops.conversation import Conversation
from companion.store.sqlite.store import Store
from companion.turn.fast import handle
from companion.turn.mode import mode_report
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Judge, Talker


async def test_mode_says_which_talker_answered_and_whether_a_scene_is_under_way(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "r.sqlite")
    assert mode_report(store, REL, NOW, "luna", "deepseek") == "no replies yet"
    convo = Conversation(store, Talker(), PREFIX, REL, judge=Judge(), roleplay_talker=Talker())
    await handle(convo, SESSION, "hey", "t", NOW)
    report = mode_report(store, REL, NOW + timedelta(minutes=1), "luna", "deepseek")
    assert "everyday talker (luna)" in report
    assert "no scene" in report
