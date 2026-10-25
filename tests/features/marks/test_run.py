from __future__ import annotations

from pathlib import Path

from companion.core.turn.listening import Judgement
from companion.core.types import Frame, TurnId
from companion.features.marks.logic import MARKS
from companion.features.marks.run import mark_offer
from companion.loops.conversation import Conversation
from companion.loops.current import Heard, Turn
from companion.loops.features import Lookups, Moment
from companion.store.sqlite.store import Store
from tests.turn.test_mood_loop import NOW, PREFIX, REL, SESSION, Talker

CALM: Heard = (Judgement(severity=0, stance="other", vague=False, age_coded=False), "j", "p")
HEAVY: Heard = (Judgement(severity=2, stance="sharing", vague=False, age_coded=False), "j", "p")


def _offer(tmp_path: Path, text: str, heard: Heard, *, marks: bool = True) -> tuple[str, ...]:
    convo = Conversation(Store(tmp_path / "r.sqlite"), Talker(), PREFIX, REL, marks=marks)
    t = Turn(SESSION, TurnId("t1"), NOW, [], text)
    return mark_offer(Moment(convo, t, Frame.REAL, heard, Lookups(), False, []), None, {}).tail


def test_their_mark_brings_one_of_its_own_after_the_history_never_theirs(tmp_path: Path) -> None:
    [line] = _offer(tmp_path, "home finally :3", CALM)
    offered = line.rsplit("yours: ", 1)[1]
    assert any(m in offered for m in MARKS)
    assert ":3" not in offered
    assert "They used :3" in line  # theirs is named as theirs, not offered


def test_switched_off_or_on_a_serious_turn_nothing_is_offered(tmp_path: Path) -> None:
    assert not _offer(tmp_path, "home finally :3", CALM, marks=False)
    assert not _offer(tmp_path, "it's been a hard week :3", HEAVY)
