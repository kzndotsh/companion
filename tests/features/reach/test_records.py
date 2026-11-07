from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from companion.core.reachout import OWN_KINDS, WOULD_NUDGE, Fate, Kind, ReachOut
from companion.core.types import (
    Frame,
    RelationshipId,
    Sensitivity,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.reach.store import Own, Reaches, records
from companion.features.threads.logic import Thread
from companion.features.threads.store import Threads
from companion.kit.record import Recorder
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
H = timedelta(hours=1)


def test_every_kind_of_reach_out_reads_back_as_one_record(tmp_path: Path) -> None:
    with Store(tmp_path / "rel.sqlite") as store:
        store.part(Reaches).add(
            Own("o1", REL, Kind.THOUGHT, "t1", "saw a cat", Fate.SHADOW, {}, T0)
        )
        store.part(Reaches).add(
            Own("o2", REL, Kind.MISSING, "", "", Fate.DROPPED, {"dial": "warm"}, T0 + 3 * H)
        )
        Recorder.fresh(store, REL, T0 + H).decide(
            WOULD_NUDGE, {"draft": "back soon?", "said": "shower"}
        )
        store.append_utterance(
            Utterance(UtteranceId("u"), REL, TurnId("t"), Speaker.USER, "vet", Frame.REAL, "x", T0)
        )
        store.part(Threads).add_loop(
            Thread("l1", REL, "vet", "vet", UtteranceId("u"), T0 + H, Sensitivity.ORDINARY, T0)
        )
        store.add_reach_out(
            ReachOut("p1", REL, "l1", Fate.LIVE, "how did it go?", "due", T0 + 2 * H)
        )
        got = records(store, REL)
        own = records(store, REL, T0, OWN_KINDS)
        later = records(store, REL, T0 + 2 * H)

    assert [(r.kind, r.fate, r.text) for r in got] == [
        (Kind.THOUGHT, Fate.SHADOW, "saw a cat"),
        (Kind.AWAY, Fate.SHADOW, "back soon?"),
        (Kind.PLAN, Fate.LIVE, "how did it go?"),
        (Kind.MISSING, Fate.DROPPED, ""),
    ]
    assert [r.live for r in got] == [False, False, True, False]
    assert [r.id for r in own] == ["o1", "o2"]
    assert [r.id for r in later] == ["p1", "o2"]
    assert got[2].detail == {"loop_id": "l1", "reason": "due"}
