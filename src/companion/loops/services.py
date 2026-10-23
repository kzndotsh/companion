"""What a one-off command's job is handed: the store, the judges' model and the relationship. The
model is metered, so what a command spends counts toward the day's spend. Opened and closed by
`companion/commands.py`."""

from __future__ import annotations

from dataclasses import dataclass

from companion.core.extractor import Extractor
from companion.core.types import RelationshipId
from companion.store.sqlite.store import Store


@dataclass(frozen=True, slots=True)
class Services:
    store: Store
    judge: Extractor
    rel: RelationshipId
