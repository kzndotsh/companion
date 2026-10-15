from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from companion.core.extractor import Extraction
from companion.core.types import (
    Frame,
    Json,
    RelationshipId,
    SessionId,
    Speaker,
    TurnId,
    Utterance,
    UtteranceId,
)
from companion.loops.slow import reflect_once
from companion.store.sqlite.store import Store

REL = RelationshipId("rel")
T0 = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


class FakeExtractor:
    def __init__(self, *responses: Json) -> None:
        self.responses = list(responses)
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        self.calls += 1
        return Extraction(data=self.responses.pop(0), model="fake", cost_usd=0.001, latency_ms=3)


class BoomExtractor:
    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        msg = "provider down"
        raise RuntimeError(msg)


def _say(store: Store, n: int, speaker: Speaker, text: str) -> Utterance:
    u = Utterance(
        UtteranceId(f"u{n}"),
        REL,
        SessionId("s"),
        TurnId(f"t{n}"),
        speaker,
        text,
        Frame.REAL,
        "test",
        T0 + timedelta(minutes=n),
    )
    store.append_utterance(u)
    return u


def _belief(ref: str, quote: str, claim: str, **over: Json) -> Json:
    base: dict[str, Json] = {
        "ref": ref,
        "quote": quote,
        "claim": claim,
        "subject": "user",
        "kind": "trait",
        "provenance": "stated",
        "confidence": 0.9,
        "sensitivity": 1,
    }
    base.update(over)
    return base


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "rel.sqlite")


async def test_verified_beliefs_are_stored_with_their_evidence(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have ocd and adhd")
    _say(store, 2, Speaker.COMPANION, "that makes sense")
    ex = FakeExtractor({"beliefs": [_belief("m1", "ocd and adhd", "Has OCD and ADHD")]})
    result = await reflect_once(store, ex, REL, T0 + timedelta(hours=1))
    assert (result.accepted, result.rejected) == (1, 0)
    [b] = store.current_beliefs(REL)
    assert b.evidence[0].quote == "ocd and adhd"
    assert b.confidence == 0.6


async def test_a_fabricated_quote_is_rejected_and_logged(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have ocd and adhd")
    ex = FakeExtractor({"beliefs": [_belief("m1", "i have bipolar", "Has bipolar")]})
    result = await reflect_once(store, ex, REL, T0 + timedelta(hours=1))
    assert (result.accepted, result.rejected) == (0, 1)
    assert store.current_beliefs(REL) == []


async def test_the_log_is_the_cursor_so_a_second_pass_reads_nothing(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have ocd and adhd")
    ex = FakeExtractor({"beliefs": []})
    assert (await reflect_once(store, ex, REL)).ran
    assert not (await reflect_once(store, ex, REL)).ran
    assert ex.calls == 1


async def test_only_new_utterances_are_read_on_the_next_pass(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have ocd and adhd")
    ex = FakeExtractor({"beliefs": []}, {"beliefs": []})
    await reflect_once(store, ex, REL)
    _say(store, 2, Speaker.USER, "i like climbing")
    result = await reflect_once(store, ex, REL)
    assert result.ran
    assert ex.calls == 2


async def test_a_repeated_claim_is_not_stored_twice(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have ocd and adhd")
    one: Json = {"beliefs": [_belief("m1", "i have ocd and adhd", "Has OCD and ADHD")]}
    ex = FakeExtractor(one)
    await reflect_once(store, ex, REL)
    _say(store, 2, Speaker.USER, "like i said, i have ocd and adhd")
    again: Json = {"beliefs": [_belief("m2", "i have ocd and adhd", "has ocd and adhd.")]}
    ex2 = FakeExtractor(again)
    result = await reflect_once(store, ex2, REL)
    assert (result.accepted, result.duplicates) == (0, 1)
    assert len(store.current_beliefs(REL)) == 1


async def test_a_batch_with_only_companion_words_skips_the_model(store: Store) -> None:
    _say(store, 1, Speaker.COMPANION, "hello there")
    ex = FakeExtractor()
    result = await reflect_once(store, ex, REL)
    assert result.ran
    assert ex.calls == 0


async def test_a_failed_model_call_does_not_advance_the_cursor(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have ocd and adhd")
    with pytest.raises(RuntimeError):
        await reflect_once(store, BoomExtractor(), REL)
    ex = FakeExtractor({"beliefs": []})
    assert (await reflect_once(store, ex, REL)).ran
    assert ex.calls == 1


async def test_a_malformed_response_is_logged_and_still_advances(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have ocd and adhd")
    ex = FakeExtractor({"nonsense": True})
    result = await reflect_once(store, ex, REL)
    assert result.rejected == 1
    assert not (await reflect_once(store, ex, REL)).ran


async def test_a_paraphrase_resting_on_the_same_words_is_a_duplicate(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i hate cooking, im so lazy lol")
    ex = FakeExtractor(
        {
            "beliefs": [
                _belief("m1", "i hate cooking", "User hates cooking."),
                _belief("m1", "i hate cooking, im so lazy", "User hates cooking and is lazy."),
            ]
        }
    )
    result = await reflect_once(store, ex, REL)
    assert (result.accepted, result.duplicates) == (1, 1)
