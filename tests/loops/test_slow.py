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
        data: Json = self.responses.pop(0) if self.responses else {"beliefs": []}
        return Extraction(data=data, model="fake", cost_usd=0.001, latency_ms=3)


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
    _say(store, 1, Speaker.USER, "i have asthma and a bad knee")
    _say(store, 2, Speaker.COMPANION, "that makes sense")
    ex = FakeExtractor(
        {"beliefs": [_belief("m1", "asthma and a bad knee", "Has asthma and a bad knee")]}
    )
    result = await reflect_once(store, ex, REL, T0 + timedelta(hours=1))
    assert (result.accepted, result.rejected) == (1, 0)
    [b] = store.current_beliefs(REL)
    assert b.evidence[0].quote == "asthma and a bad knee"
    assert b.confidence == 0.6


async def test_a_fabricated_quote_is_rejected_and_logged(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have asthma and a bad knee")
    ex = FakeExtractor({"beliefs": [_belief("m1", "i have bipolar", "Has bipolar")]})
    result = await reflect_once(store, ex, REL, T0 + timedelta(hours=1))
    assert (result.accepted, result.rejected) == (0, 1)
    assert store.current_beliefs(REL) == []


async def test_the_log_is_the_cursor_so_a_second_pass_reads_nothing(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have asthma and a bad knee")
    ex = FakeExtractor({"beliefs": []})
    assert (await reflect_once(store, ex, REL)).ran
    assert not (await reflect_once(store, ex, REL)).ran
    assert ex.calls == 2  # the beliefs pass and the open-loops pass, once


async def test_only_new_utterances_are_read_on_the_next_pass(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have asthma and a bad knee")
    ex = FakeExtractor({"beliefs": []}, {"beliefs": []})
    await reflect_once(store, ex, REL)
    _say(store, 2, Speaker.USER, "i like climbing")
    result = await reflect_once(store, ex, REL)
    assert result.ran
    assert ex.calls == 4  # two reads, each a beliefs pass and an open-loops pass


async def test_a_repeated_claim_is_not_stored_twice(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have asthma and a bad knee")
    one: Json = {
        "beliefs": [_belief("m1", "i have asthma and a bad knee", "Has asthma and a bad knee")]
    }
    ex = FakeExtractor(one)
    await reflect_once(store, ex, REL)
    _say(store, 2, Speaker.USER, "like i said, i have asthma and a bad knee")
    again: Json = {
        "beliefs": [_belief("m2", "i have asthma and a bad knee", "has asthma and a bad knee.")]
    }
    ex2 = FakeExtractor(again)
    result = await reflect_once(store, ex2, REL)
    assert (result.accepted, result.duplicates) == (0, 1)
    assert len(store.current_beliefs(REL)) == 1


async def test_a_batch_with_only_companion_words_gets_only_the_self_pass(store: Store) -> None:
    _say(store, 1, Speaker.COMPANION, "hello there")
    ex = FakeExtractor()
    result = await reflect_once(store, ex, REL)
    assert result.ran
    assert ex.calls == 1  # the user pass is skipped, the self pass runs


async def test_a_failed_model_call_does_not_advance_the_cursor(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have asthma and a bad knee")
    with pytest.raises(RuntimeError):
        await reflect_once(store, BoomExtractor(), REL)
    ex = FakeExtractor({"beliefs": []})
    assert (await reflect_once(store, ex, REL)).ran
    assert ex.calls == 2


async def test_a_malformed_response_is_logged_and_still_advances(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i have asthma and a bad knee")
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


class _Spy(FakeExtractor):
    def __init__(self, *responses: Json) -> None:
        super().__init__(*responses)
        self.prompts: list[str] = []

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        self.prompts.append(user)
        return await super().extract(system, user, schema)


def _restatement(ref: str, quote: str, label: str) -> Json:
    return {**_belief(ref, quote, "Feels lonely lately.", kind="state"), "confirms": label}  # type: ignore[dict-item]


async def test_a_restatement_refreshes_the_belief_with_new_evidence(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i feel so lonely lately")
    first = _Spy(
        {"beliefs": [_belief("m1", "so lonely lately", "Feels lonely lately.", kind="state")]}
    )
    await reflect_once(store, first, REL, T0 + timedelta(hours=1))
    [b] = store.current_beliefs(REL)
    before = store.last_support(REL)[b.id]

    later = _say(store, 2, Speaker.USER, "honestly still lonely")
    spy = _Spy({"beliefs": [_restatement("m2", "still lonely", "k1")]})
    result = await reflect_once(store, spy, REL, T0 + timedelta(days=9))

    assert "[k1] Feels lonely lately." in spy.prompts[0]
    assert (result.accepted, result.confirmed, result.rejected) == (0, 1, 0)
    assert [x.id for x in store.current_beliefs(REL)] == [b.id]
    assert store.last_support(REL)[b.id] == later.at > before
    assert {e.utterance_id for e in store.current_beliefs(REL)[0].evidence} == {"u1", "u2"}


async def test_a_confirmation_pointing_nowhere_is_rejected_and_logged(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i feel so lonely lately")
    ex = FakeExtractor({"beliefs": [_restatement("m1", "so lonely", "k5")]})
    result = await reflect_once(store, ex, REL)
    assert (result.confirmed, result.rejected) == (0, 1)
    assert store.current_beliefs(REL) == []


async def test_a_fabricated_restatement_quote_never_attaches(store: Store) -> None:
    _say(store, 1, Speaker.USER, "i feel so lonely lately")
    await reflect_once(
        store,
        FakeExtractor(
            {"beliefs": [_belief("m1", "so lonely", "Feels lonely lately.", kind="state")]}
        ),
        REL,
    )
    _say(store, 2, Speaker.USER, "okay going to sleep now")
    result = await reflect_once(
        store, FakeExtractor({"beliefs": [_restatement("m2", "still lonely", "k1")]}), REL
    )
    assert (result.confirmed, result.rejected) == (0, 1)
    [b] = store.current_beliefs(REL)
    assert len(b.evidence) == 1
