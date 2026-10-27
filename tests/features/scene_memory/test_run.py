from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import timedelta
from pathlib import Path

import pytest

from companion.cli.beliefs import retire_one
from companion.core.extractor import Extraction
from companion.core.turn.floor import MINOR_KEY
from companion.core.types import (
    Belief,
    BeliefId,
    BeliefKind,
    Evidence,
    Frame,
    Json,
    Provenance,
    SessionId,
    Speaker,
    Subject,
    TraceId,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.features.scene_memory import run
from companion.features.scene_memory.cli import run as listing
from companion.features.scene_memory.logic import (
    LANE,
    LIMIT_CHECK,
    PATTERN,
    Everyday,
    Excluded,
    Intimate,
    Stance,
    Why,
)
from companion.features.scene_memory.run import (
    NOTED,
    PLACED,
    UNREAD,
    entries,
    label_lanes,
    pass_step,
    read_scenes,
)
from companion.loops.record import Recorder
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0

LATER = T0 + timedelta(days=2)
# claim -> (lane, stance) for each of the three reads
Lanes = Callable[[int, str], tuple[str, str]]


def _agreed(lane: str, stance: str) -> Lanes:
    return lambda _n, _claim: (lane, stance)


class Judge:
    """Answers the lane reads with `lanes` (read number, claim) and the scene reads with a pattern
    for each of their messages holding one of `plays` (phrase, claim, stance)."""

    def __init__(
        self,
        lanes: Mapping[str, Lanes] | None = None,
        plays: tuple[tuple[str, str, str], ...] = (),
        *,
        fail: bool = False,
        not_limits: frozenset[str] = frozenset(),
    ) -> None:
        self.lanes, self.plays, self.fail = lanes or {}, plays, fail
        self.not_limits = not_limits  # claims the limit check says set no limit
        self.calls: list[str] = []
        self.reads = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del schema
        if self.fail:
            msg = "down"
            raise RuntimeError(msg)
        if system == LANE.text:
            self.calls.append("lane")
            n, self.reads = self.reads % 3, self.reads + 1
            labels: list[Json] = []
            for ref, claim in re.findall(r"^\[(b\d+)\] (.+?) \(they said", user, re.MULTILINE):
                lane, stance = self.lanes.get(claim, _agreed("everyday", "none"))(n, claim)
                labels.append({"ref": ref, "lane": lane, "stance": stance})
            return Extraction({"labels": labels}, "fake", 0.001, 1)
        if system == LIMIT_CHECK.text:
            self.calls.append("limit")
            meant = user.split("\n", 1)[0].removeprefix("What it was taken to mean: ")
            return Extraction({"limit": meant not in self.not_limits}, "fake", 0.001, 1)
        assert system == PATTERN.text
        self.calls.append("scene")
        noted = dict(re.findall(r"^\[(p\d+)\] (.+)$", user, re.MULTILINE))
        found: list[Json] = []
        for label, text in re.findall(r"^\[(m\d+)\] USER: (.+)$", user, re.MULTILINE):
            for phrase, claim, stance in self.plays:
                if phrase in text:
                    ref = next((r for r, c in noted.items() if c == claim), "")
                    found.append(
                        {
                            "pattern": ref,
                            "claim": claim,
                            "stance": stance,
                            "message": label,
                            "quote": phrase,
                        }
                    )
        return Extraction({"patterns": found}, "fake", 0.001, 1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _say(store: Store, text: str, frame: Frame = Frame.REAL, minutes: int = 0) -> Utterance:
    n = len(store.history_before(REL, LATER, 1000)) + 1
    u = Utterance(
        UtteranceId(f"u{n}"),
        REL,
        SessionId("s"),
        TurnId(f"t{n}"),
        Speaker.USER,
        text,
        frame,
        "test",
        T0 + timedelta(minutes=minutes or n),
    )
    store.append_utterance(u)
    return u


def _told(store: Store, claim: str, said: str, **kw: object) -> Belief:
    u = _say(store, said)
    fields: dict[str, object] = {
        "id": BeliefId(f"b-{u.id}"),
        "relationship_id": REL,
        "subject": Subject.USER,
        "kind": BeliefKind.PREFERENCE,
        "claim": claim,
        "evidence": (Evidence(u.id, said),),
        "provenance": Provenance.STATED,
        "speaker": Speaker.USER,
        "frame": Frame.REAL,
        "confidence": 0.6,
        "valid_from": u.at,
        "recorded_at": u.at,
    } | kw
    b = Belief(**fields)  # type: ignore[arg-type]
    store.insert_belief(b)
    return b


def _source(store: Store, b: Belief) -> Utterance:
    u = store.get_utterance(b.evidence[0].utterance_id)
    assert u is not None
    return u


def _decide(store: Store, u: Utterance, key: str, detail: dict[str, Json]) -> None:
    Recorder(store, REL, u.session_id, u.turn_id, TraceId("x"), u.at).decide(key, detail)


async def test_three_reads_place_a_memory_by_lane_with_the_stance_most_of_them_gave(
    store: Store,
) -> None:
    into = _told(store, "likes slow kissing", "i love slow kissing")
    split = _told(store, "wants to try blindfolds", "maybe blindfolds someday")
    work = _told(store, "works as a nurse", "i work nights as a nurse")
    judge = Judge(
        {
            into.claim: _agreed("intimate", "into"),
            split.claim: lambda n, _: ("intimate", "curious" if n else "into"),
        }
    )
    await label_lanes(store, judge, REL, LATER)
    assert judge.calls == ["lane"] * 3
    assert store.scene_memory().places(REL) == {
        into.id: Intimate(Stance.INTO),
        split.id: Intimate(Stance.CURIOUS),
        work.id: Everyday(),
    }
    logged = {d.reason for d in store.decisions_with_key(REL, PLACED)}
    assert logged == {"scene memory: intimate, into", "scene memory: intimate, curious"}


async def test_a_failed_read_places_nothing_and_the_batch_waits(store: Store) -> None:
    _told(store, "likes slow kissing", "i love slow kissing")
    await label_lanes(store, Judge(fail=True), REL, LATER)
    assert store.scene_memory().places(REL) == {}


async def test_the_floor_keeps_out_a_held_turn_and_heavy_sharing_whatever_the_reads_say(
    store: Store,
) -> None:
    held = _told(store, "likes being teased", "i like being teased")
    heavy = _told(store, "likes being held after", "i need to be held after")
    _decide(store, _source(store, held), MINOR_KEY, {"minor": True})
    _decide(store, _source(store, heavy), "listening", {"labels": {"severity": 2}})
    judge = Judge(
        {held.claim: _agreed("intimate", "into"), heavy.claim: _agreed("intimate", "aftercare")}
    )
    await label_lanes(store, judge, REL, LATER)
    assert store.scene_memory().places(REL) == {
        held.id: Excluded(Why.FLOOR),
        heavy.id: Excluded(Why.LISTENING),
    }
    assert entries(store, REL) == ()


async def test_a_limit_read_into_an_inferred_memory_is_not_their_words(store: Store) -> None:
    stated = _told(store, "never wants choking", "no choking, ever")
    inferred = _told(store, "seems not to want pain", "ouch haha", provenance=Provenance.INFERRED)
    limit = _agreed("intimate", "hard_limit")
    await label_lanes(store, Judge({stated.claim: limit, inferred.claim: limit}), REL, LATER)
    assert store.scene_memory().places(REL) == {
        stated.id: Intimate(Stance.HARD_LIMIT),
        inferred.id: Excluded(Why.NOT_THEIR_WORDS),
    }
    assert [e.id for e in entries(store, REL)] == [stated.id]


async def test_a_limit_the_narrow_check_does_not_confirm_is_kept_out_as_doubt(
    store: Store,
) -> None:
    wish = _told(store, "wishes it could hold the companion", "i can't hold you :c")
    limit = _agreed("intimate", "soft_limit")
    judge = Judge({wish.claim: limit}, not_limits=frozenset({wish.claim}))
    await label_lanes(store, judge, REL, LATER)
    assert store.scene_memory().places(REL) == {wish.id: Excluded(Why.DOUBT)}
    assert judge.calls.count("limit") == 3


SLOW = "In scenes, the user tends to ask for a slow pace."
PLAYS = (("slower please", SLOW, "style"), ("tie my hands", "In scenes, no.", "hard_limit"))


def _scene(store: Store, start: int, *lines: str) -> None:
    for n, line in enumerate(lines):
        _say(store, line, Frame.PLAY, start + n)
    _say(store, "ok back to real life", Frame.REAL, start + len(lines))


async def test_a_pattern_reaches_the_lane_only_once_seen_in_two_separate_scenes(
    store: Store, tmp_path: Path
) -> None:
    _scene(store, 10, "*steps closer* slower please", "*smiles*")
    await read_scenes(store, Judge(plays=PLAYS), REL, LATER)
    [pattern] = store.scene_memory().patterns(REL)
    assert pattern.scenes == 1
    assert entries(store, REL) == ()
    assert "patterns seen in one scene so far" in listing(tmp_path / "rel.sqlite", REL)
    _scene(store, 300, "*laughs* slower please, again")
    await read_scenes(store, Judge(plays=PLAYS), REL, LATER)
    [pattern] = store.scene_memory().patterns(REL)
    assert pattern.scenes == 2
    [entry] = entries(store, REL)
    assert (entry.claim, entry.stance, entry.scenes) == (SLOW, Stance.STYLE, 2)
    assert sorted(d.reason for d in store.decisions_with_key(REL, NOTED)) == [
        f"{NOTED}: seen in 1 scene(s)",
        f"{NOTED}: seen in 2 scene(s)",
    ]


async def test_a_limit_is_never_taken_from_play(store: Store) -> None:
    _scene(store, 10, "*grins* tie my hands")
    _scene(store, 300, "*grins* tie my hands")
    await read_scenes(store, Judge(plays=PLAYS), REL, LATER)
    assert store.scene_memory().patterns(REL) == []


async def test_a_scene_with_a_turn_the_minor_check_held_is_never_read(store: Store) -> None:
    _scene(store, 10, "*steps closer* slower please")
    first = store.history_before(REL, LATER, 10)[0]
    _decide(store, first, MINOR_KEY, {"minor": True})
    judge = Judge(plays=PLAYS)
    await read_scenes(store, judge, REL, LATER)
    assert judge.calls == []
    assert store.scene_memory().patterns(REL) == []
    [unread] = store.decisions_with_key(REL, UNREAD)
    assert "slower" not in str(unread.detail)


async def test_a_failed_scene_read_leaves_the_bookmark_for_the_next_pass(store: Store) -> None:
    _scene(store, 10, "*steps closer* slower please")
    await read_scenes(store, Judge(fail=True), REL, LATER)
    assert store.scene_memory().cursor(REL) is None
    await read_scenes(store, Judge(plays=PLAYS), REL, LATER)
    assert len(store.scene_memory().patterns(REL)) == 1


async def test_a_scene_still_going_waits(store: Store) -> None:
    _say(store, "*steps closer* slower please", Frame.PLAY, 10)
    judge = Judge(plays=PLAYS)
    await read_scenes(store, judge, REL, T0 + timedelta(minutes=30))
    assert judge.calls == []
    assert store.scene_memory().cursor(REL) is None


async def test_the_listing_shows_only_the_id_of_what_the_floor_kept_out(
    store: Store, tmp_path: Path
) -> None:
    kept = _told(store, "likes slow kissing", "i love slow kissing")
    floor = _told(store, "likes roleplay at 17", "pretend i'm 17")
    doubt = _told(store, "wants to try blindfolds", "maybe blindfolds someday")
    judge = Judge(
        {
            kept.claim: _agreed("intimate", "into"),
            floor.claim: _agreed("intimate", "into"),
            doubt.claim: lambda n, _: (
                "everyday" if n else "intimate",
                "into" if not n else "none",
            ),
        }
    )
    await label_lanes(store, judge, REL, LATER)
    out = listing(tmp_path / "rel.sqlite", REL)
    assert f"{kept.id[:8]}  {kept.claim}" in out
    assert '"i love slow kissing"' in out
    assert f"{floor.id[:8]}  excluded by the floor" in out
    assert "17" not in out
    assert f"{doubt.claim}  (the three reads did not agree)" in out


async def test_retire_works_for_a_pattern_and_it_leaves_the_lane(
    store: Store, tmp_path: Path
) -> None:
    _scene(store, 10, "*steps closer* slower please")
    _scene(store, 300, "*steps closer* slower please")
    await read_scenes(store, Judge(plays=PLAYS), REL, LATER)
    [pattern] = store.scene_memory().patterns(REL)
    out = retire_one(tmp_path / "rel.sqlite", REL, pattern.id[:8], "the owner does not want it")
    assert out.startswith("retired")
    assert entries(store, REL) == ()
    assert "retired patterns" in listing(tmp_path / "rel.sqlite", REL)


async def test_switch_off_has_no_pass_step(store: Store) -> None:
    assert pass_step("off") is None
    _told(store, "likes slow kissing", "i love slow kissing")
    step = pass_step("shadow")
    assert step is not None
    await step(store, Judge({"likes slow kissing": _agreed("intimate", "into")}), REL, LATER)
    assert len(store.scene_memory().places(REL)) == 1


async def test_a_scene_cut_by_the_end_of_a_full_batch_waits_to_be_read_whole(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run, "READ", 3)
    first = _say(store, "hey", Frame.REAL, 1)
    for n in range(4):
        _say(store, f"*steps closer* slower please {n}", Frame.PLAY, 2 + n)
    judge = Judge(plays=PLAYS)
    await read_scenes(store, judge, REL, LATER)
    assert judge.calls == []
    assert store.scene_memory().cursor(REL) == (first.at, first.id)
