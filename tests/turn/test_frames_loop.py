from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.prompt.prefix import build_prefix
from companion.core.prompt.request import TalkerRequest
from companion.core.talker import Reply
from companion.core.types import Frame, Json, RelationshipId, SessionId, Speaker
from companion.loops.runtime import Runtime
from companion.store.sqlite.store import Store
from companion.turn import frames as frames_loop
from companion.turn.fast import handle

REL = RelationshipId("rel")
SESSION = SessionId("s")
PREFIX = build_prefix("You are steady and warm. " * 200)
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)


class Talker:
    def __init__(self, *texts: str, fail_on: int | None = None) -> None:
        self.texts = list(texts)
        self.seen: list[TalkerRequest] = []
        self.fail_on = fail_on

    async def reply(self, request: TalkerRequest) -> Reply:
        self.seen.append(request)
        if self.fail_on == len(self.seen):
            msg = "provider down"
            raise RuntimeError(msg)
        await asyncio.sleep(0.01)
        return Reply(self.texts.pop(0), "m", 5)


class Judge:
    """Answers the frame judgement; any other call gets an inert answer."""

    def __init__(self, *frames: tuple[str, float], fail: bool = False, delay: float = 0.0) -> None:
        self.frames = list(frames)
        self.calls = 0
        self.fail = fail
        self.delay = delay

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        if "label the frame" not in system:
            return Extraction({"kind": "other", "confidence": 0.1, "emoji": "👍"}, "j", 0.0, 1)
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            msg = "down"
            raise RuntimeError(msg)
        frame, conf = self.frames.pop(0) if self.frames else ("real", 0.9)
        return Extraction({"frame": frame, "confidence": conf}, "judge-model", 0.0, 1)


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


def _frames(store: Store) -> list[tuple[str, Frame]]:
    rows = store.history_before(REL, NOW + timedelta(days=1), 50)
    return [(u.text, u.frame) for u in rows]


async def test_an_ordinary_message_is_stored_real_and_never_asks_the_judge(store: Store) -> None:
    judge = Judge()
    await handle(
        Runtime(store, Talker("hey"), PREFIX, REL, judge=judge),
        SESSION,
        "i got a haircut",
        "t",
        NOW,
    )
    assert judge.calls == 0
    assert all(f is Frame.REAL for _, f in _frames(store))


async def test_a_pretend_message_is_stored_as_play_and_the_companion_plays_along(
    store: Store,
) -> None:
    judge = Judge(("play", 0.92))
    await handle(
        Runtime(store, Talker("*slides a plate over*"), PREFIX, REL, judge=judge),
        SESSION,
        "can't we pretend you cooked me lunch",
        "t",
        NOW,
    )
    assert _frames(store) == [
        ("can't we pretend you cooked me lunch", Frame.PLAY),
        ("*slides a plate over*", Frame.PLAY),
    ]


async def test_a_low_confidence_judgement_stores_real(store: Store) -> None:
    judge = Judge(("play", 0.4))
    await handle(
        Runtime(store, Talker("ok"), PREFIX, REL, judge=judge),
        SESSION,
        "imagine that",
        "t",
        NOW,
    )
    assert all(f is Frame.REAL for _, f in _frames(store))


async def test_a_scene_in_progress_adds_a_note_to_the_next_reply_without_waiting(
    store: Store,
) -> None:
    judge = Judge(("play", 0.9), ("play", 0.9))
    talker = Talker("*waves*", "*bows*")
    runtime = Runtime(store, talker, PREFIX, REL, judge=judge)
    await handle(runtime, SESSION, "let's pretend you're a knight", "t", NOW)
    await handle(runtime, SESSION, "and then what", "t", NOW + timedelta(seconds=30))
    assert "pretend scene" not in talker.seen[0].card
    assert "A pretend scene they started is in progress" in talker.seen[1].card
    assert "pretend scene" not in talker.seen[1].messages[-1].content
    assert judge.calls == 2  # the second message had no cue; the scene alone triggered the judge


async def test_stepping_out_ends_the_scene_and_the_companion_steps_out_too(store: Store) -> None:
    judge = Judge(("play", 0.9), ("ooc", 0.9))
    talker = Talker("*bows*", "sure, what's up")
    runtime = Runtime(store, talker, PREFIX, REL, judge=judge)
    await handle(runtime, SESSION, "let's pretend you're a knight", "t", NOW)
    await handle(runtime, SESSION, "ok stop, seriously though", "t", NOW + timedelta(seconds=30))
    last_two = _frames(store)[-2:]
    assert [f for _, f in last_two] == [Frame.OOC, Frame.REAL]
    third = Talker("hello")
    await handle(
        Runtime(store, third, PREFIX, REL, judge=judge),
        SESSION,
        "anyway",
        "t",
        NOW + timedelta(minutes=1),
    )
    assert "pretend scene" not in third.seen[0].messages[-1].content


async def test_a_failing_or_slow_judge_stores_real_and_the_reply_still_goes(
    store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = await handle(
        Runtime(store, Talker("ok"), PREFIX, REL, judge=Judge(fail=True)),
        SESSION,
        "let's pretend",
        "t",
        NOW,
    )
    assert out == "ok"
    monkeypatch.setattr(frames_loop, "FRAME", replace(frames_loop.FRAME, timeout=0.05))
    out = await handle(
        Runtime(store, Talker("fine"), PREFIX, REL, judge=Judge(("play", 0.9), delay=1.0)),
        SESSION,
        "imagine that",
        "t",
        NOW + timedelta(minutes=5),
    )
    assert out == "fine"
    assert all(f is Frame.REAL for _, f in _frames(store))


async def test_a_failed_reply_still_stores_the_users_message(store: Store) -> None:
    runtime = Runtime(store, Talker(fail_on=1), PREFIX, REL, judge=Judge(("play", 0.9)))
    with pytest.raises(RuntimeError):
        await handle(runtime, SESSION, "let's pretend", "t", NOW)
    assert _frames(store) == [("let's pretend", Frame.REAL)]


async def test_every_frame_judgement_is_logged_with_a_reason_built_by_code(
    store: Store, tmp_path: Path
) -> None:
    await handle(
        Runtime(store, Talker("*smiles*"), PREFIX, REL, judge=Judge(("play", 0.92))),
        SESSION,
        "let's pretend",
        "t",
        NOW,
    )
    turn = store.latest_turn(REL)
    assert turn is not None
    reasons = [d for d in store.decisions_for_turn(REL, turn) if "stored as" in d.reason]
    assert len(reasons) == 1
    assert reasons[0].reason == "stored as play: judged at 0.92"
    assert reasons[0].detail is not None
    assert reasons[0].detail["scores"] == {"frame": "play", "confidence": 0.92}
    assert reasons[0].detail["scorer"] == "judge-model"


async def test_replay_still_matches_when_a_scene_note_is_in_the_request(
    store: Store, tmp_path: Path
) -> None:
    import sqlite3  # noqa: PLC0415

    from companion.store.sqlite import replay as store_replay  # noqa: PLC0415

    judge = Judge(("play", 0.9), ("play", 0.9))
    runtime = Runtime(store, Talker("*a*", "*b*"), PREFIX, REL, judge=judge)
    await handle(runtime, SESSION, "let's pretend", "t", NOW)
    await handle(runtime, SESSION, "and then", "t", NOW + timedelta(seconds=30))
    store.close()
    db = tmp_path / "rel.sqlite"
    with sqlite3.connect(db) as c:
        turns = [str(r[0]) for r in c.execute("SELECT turn_id FROM turn_requests ORDER BY at")]
    assert all(store_replay.replay_file(db, t).matched for t in turns)


async def test_a_played_belief_is_recorded_but_never_reaches_the_card(store: Store) -> None:
    from companion.core.types import (  # noqa: PLC0415
        Belief,
        BeliefId,
        BeliefKind,
        Evidence,
        Provenance,
        Subject,
        TurnId,
        Utterance,
        UtteranceId,
    )

    store.append_utterance(
        Utterance(
            UtteranceId("p1"),
            REL,
            SESSION,
            TurnId("t0"),
            Speaker.USER,
            "i am a dragon with gold",
            Frame.PLAY,
            "t",
            NOW - timedelta(days=1),
        )
    )

    def believe(bid: str, claim: str, provenance: Provenance, frame: Frame) -> Belief:
        return Belief(
            id=BeliefId(bid),
            relationship_id=REL,
            subject=Subject.USER,
            kind=BeliefKind.TRAIT,
            claim=claim,
            evidence=(Evidence(UtteranceId("p1"), "i am a dragon"),),
            provenance=provenance,
            speaker=Speaker.USER,
            frame=frame,
            confidence=0.6,
            valid_from=NOW - timedelta(days=1),
            recorded_at=NOW,
        )

    store.insert_belief(believe("played", "The user is a dragon.", Provenance.PLAYED, Frame.PLAY))
    talker = Talker("hi")
    await handle(Runtime(store, talker, PREFIX, REL), SESSION, "hello", "t", NOW)
    assert "dragon" not in talker.seen[0].messages[-1].content
    assert len(store.user_beliefs(REL)) == 1  # kept as a record


async def test_the_extraction_prompt_marks_which_messages_are_pretend(store: Store) -> None:
    from companion.core.beliefs.extract import (  # noqa: PLC0415
        build_user_prompt,
        index_window,
    )
    from companion.core.types import TurnId, Utterance, UtteranceId  # noqa: PLC0415

    u = Utterance(
        UtteranceId("p1"),
        REL,
        SESSION,
        TurnId("t0"),
        Speaker.USER,
        "*hugs you*",
        Frame.PLAY,
        "t",
        NOW,
    )
    prompt = build_user_prompt(index_window([u]), {u.id}, {})
    assert "[m1] USER TARGET [play]" in prompt
