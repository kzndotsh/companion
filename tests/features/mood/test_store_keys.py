from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from companion.core.types import DecisionKind, Json, Utterance
from companion.features.mood import store as mood_store
from companion.store.sqlite import decisions
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0
from tests.store.test_decisions import make


def test_the_reaction_key_mood_reads_is_the_one_persist_writes() -> None:
    assert mood_store.REACTED == decisions.REACTED


def _judged(store: Store, said: Utterance, key: str | None, detail: dict[str, Json]) -> None:
    store.append_decision(
        make(
            DecisionKind.POLICY,
            did=f"d{len(store.decisions_for_turn(REL, said.turn_id))}-{said.id}",
            turn_id=said.turn_id,
            key=key,
            detail=detail,
        )
    )


def test_the_judges_reads_are_found_by_key_whatever_their_prompt_is_called(
    tmp_path: Path, utterance: Callable[..., Utterance]
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    renamed, old = utterance(), utterance()
    store.append_utterance(renamed)
    store.append_utterance(old)
    _judged(store, renamed, "listening", {"prompt": "system/hear@v9", "labels": {"severity": 2}})
    _judged(store, renamed, "reacted ", {"prompt": "system/tone@v9", "scores": {"tone": "funny"}})
    _judged(store, old, None, {"prompt": "system/listening@v3", "labels": {"severity": 1}})
    _judged(store, old, None, {"prompt": "system/react@v2", "scores": {"tone": "sweet"}})
    got = [(s.severity, s.tone) for s in store.said_since(REL, T0)]
    assert got == [(2, "funny"), (1, "sweet")]
