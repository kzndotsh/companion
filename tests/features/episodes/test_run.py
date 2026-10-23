from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from companion.core.extractor import Extraction
from companion.core.types import Json, Utterance
from companion.features.episodes.run import write_closed
from companion.store.sqlite.store import Store
from tests.conftest import REL, T0


class Writer:
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, system: str, user: str, schema: dict[str, Json]) -> Extraction:
        del system, user, schema
        self.calls += 1
        return Extraction({"gist": "They talked a while; it ended warm."}, "j", 0.001, 1)


async def test_only_finished_stretches_are_written_and_never_twice(
    tmp_path: Path, utterance: Callable[..., Utterance]
) -> None:
    store = Store(tmp_path / "rel.sqlite")
    from dataclasses import replace  # noqa: PLC0415

    store.append_utterance(utterance(text="hey", uid="u1"))
    store.append_utterance(replace(utterance(text="later", uid="u2"), at=T0 + timedelta(hours=5)))
    writer = Writer()
    done = await write_closed(store, writer, REL, T0 + timedelta(hours=5, minutes=10))
    assert done.written == 1  # the second stretch is still going
    [e] = store.episodes(REL)
    assert (e.first_id, e.gist, e.kind) == ("u1", "They talked a while; it ended warm.", "everyday")
    later = await write_closed(store, writer, REL, T0 + timedelta(hours=9))
    assert later.written == 1
    assert len(store.episodes(REL)) == 2
    assert (await write_closed(store, writer, REL, T0 + timedelta(hours=10))).written == 0
